"""SDK wiring: credential check, host guard, extract options, crawl tools, feature detection.

All HTTP is served by httpx.MockTransport; no live Diffbot calls.
"""

import json

import httpx
import pytest
import yaml
from diffbot import Diffbot

from provider.diffbot import DiffbotProvider
from tools import sdk
from tools.client import DiffbotError
from tools.crawl_jobs import CrawlJobsTool
from tools.crawl_start import CrawlStartTool
from tools.extract import ExtractTool
from tools.search_organizations import SearchOrganizationsTool
from tools.search_web import SearchWebTool

TOKEN = "a" * 32
CREDS = {"diffbot_token": TOKEN}


@pytest.fixture(autouse=True, params=["native", "legacy"])
def sdk_flavor(request, monkeypatch):
    """Run every test against the SDK as installed (3.3.0 methods) and against an SDK
    without them, which exercises the plugin's client.request() fallbacks."""
    if request.param == "legacy":
        monkeypatch.delattr(Diffbot, "verify_token")
        monkeypatch.delattr(Diffbot, "crawl_download")
        real_extract = Diffbot.extract

        def old_extract(self, url, api="analyze", fmt="markdown"):
            return real_extract(self, url, api, fmt)

        monkeypatch.setattr(Diffbot, "extract", old_extract)
    return request.param


@pytest.fixture
def serve(monkeypatch):
    """Install ``handler(request) -> httpx.Response``; returns the list of seen requests."""
    seen: list[httpx.Request] = []

    def install(handler):
        def wrapped(request):
            seen.append(request)
            return handler(request)

        monkeypatch.setattr("tools.sdk.httpx.HTTPTransport", lambda **_: httpx.MockTransport(wrapped))
        return seen

    return install


def _json(messages):
    return [m for m in messages if m.type.value == "json"][-1].message.json_object


# ------------------------------------------------------------ credentials


def test_validation_calls_account_with_days_1_and_never_surfaces_payload(serve):
    seen = serve(lambda r: httpx.Response(200, json={"token": TOKEN, "plan": "FREE"}))
    DiffbotProvider()._validate_credentials(CREDS)
    assert seen[0].url.path == "/v4/account"
    assert seen[0].url.params["days"] == "1"


def test_validation_rejects_auth_failure_without_echoing_token(serve):
    serve(lambda r: httpx.Response(401, json={"error": f"bad {TOKEN}"}))
    with pytest.raises(Exception, match="Invalid or unauthorized") as caught:
        DiffbotProvider()._validate_credentials(CREDS)
    assert TOKEN not in str(caught.value)


def test_validation_does_not_treat_server_errors_as_a_bad_token(serve):
    serve(lambda r: httpx.Response(400, json={"message": "bad request"}))
    with pytest.raises(Exception) as caught:
        DiffbotProvider()._validate_credentials(CREDS)
    assert "Invalid or unauthorized" not in str(caught.value)


def test_non_json_body_is_a_safe_error(serve):
    serve(lambda r: httpx.Response(200, text="<html>oops</html>"))
    with pytest.raises(DiffbotError, match="non-JSON"):
        list(SearchWebTool.from_credentials(CREDS).invoke({"query": "x"}))


@pytest.mark.parametrize("value", ["abc", "4", "301", "-1"])
def test_request_timeout_is_validated(value):
    with pytest.raises(DiffbotError, match="timeout"):
        sdk.make_client({**CREDS, "request_timeout": value})


def test_request_timeout_is_applied():
    client = sdk.make_client({**CREDS, "request_timeout": "45"})
    assert client._http.timeout.read == 45.0  # test-only peek at the httpx client


def test_native_verify_token_is_preferred():
    class Fake:
        def verify_token(self):
            return False

    assert sdk.verify_token(Fake()) is False  # type: ignore[arg-type]


# ------------------------------------------------------------ host guard


def test_transport_blocks_private_hosts_before_any_socket():
    inner_calls = []
    inner = httpx.MockTransport(lambda r: inner_calls.append(r) or httpx.Response(200, json={}))
    client = Diffbot(TOKEN, analyze_url="http://169.254.169.254/v3", transport=sdk.GuardedTransport(inner))
    with pytest.raises(DiffbotError, match="not allowed"):
        client.extract("https://example.org")
    assert inner_calls == []


def test_default_transport_honors_proxy_environment(monkeypatch):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.org:3128")
    monkeypatch.setenv("NO_PROXY", "nl.diffbot.com")
    guard = sdk.GuardedTransport()
    assert guard._transport_for(httpx.URL("https://api.diffbot.com/v3/analyze")) is guard._proxied["https"]
    assert guard._transport_for(httpx.URL("https://nl.diffbot.com/v1/")) is guard._inner
    assert guard._transport_for(httpx.URL("http://api.diffbot.com/")) is guard._inner  # no HTTP_PROXY
    guard.close()


def test_explicit_inner_transport_ignores_proxy_environment(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.org:3128")
    inner = httpx.MockTransport(lambda r: httpx.Response(200))
    assert sdk.GuardedTransport(inner)._transport_for(httpx.URL("https://api.diffbot.com/")) is inner


def test_guard_can_be_disabled_for_self_hosted_gateways():
    inner = httpx.MockTransport(lambda r: httpx.Response(200, json={"objects": []}))
    client = Diffbot(
        TOKEN, analyze_url="http://10.0.0.5/v3", transport=sdk.GuardedTransport(inner, block_private_hosts=False)
    )
    assert client.extract("https://example.org") == {"objects": []}


def test_rate_limit_maps_to_a_safe_message(serve):
    serve(lambda r: httpx.Response(429, json={"message": TOKEN}, headers={"retry-after": "0"}))
    with pytest.raises(DiffbotError, match="rate limit") as caught:
        list(SearchWebTool.from_credentials(CREDS).invoke({"query": "x"}))
    assert TOKEN not in str(caught.value)


# ------------------------------------------------------------ extract


def test_extract_normalizes_bare_domains(serve):
    seen = serve(lambda r: httpx.Response(200, json={"objects": []}))
    list(ExtractTool.from_credentials(CREDS).invoke({"url": "example.org/story"}))
    assert seen[0].url.params["url"] == "https://example.org/story"


@pytest.mark.parametrize("url", ["localhost", "127.0.0.1/admin", "10.1.2.3", "metadata.google.internal"])
def test_extract_rejects_private_bare_domains(url):
    with pytest.raises(DiffbotError, match="not allowed"):
        list(ExtractTool.from_credentials(CREDS).invoke({"url": url}))


def test_extract_options_reach_the_request(serve):
    seen = serve(lambda r: httpx.Response(200, json={"objects": []}))
    params = {
        "url": "https://example.org",
        "fields": "links, meta",
        "timeout": 60000,
        "mode": "llm",
        "paging": True,
        "fallback": "article",
        "use_proxy": "none",
        "natural_language": "entities, summary",
        "max_pages": 3,
        "tag_confidence": 0.5,
    }
    list(ExtractTool.from_credentials(CREDS).invoke(params))
    q = seen[0].url.params
    assert q["fields"] == "links,meta"
    assert q["timeout"] == "60000"
    assert q["mode"] == "llm"
    assert q["paging"] == "true"
    assert q["maxPages"] == "3"
    assert q["tagConfidence"] == "0.5"
    assert q["fallback"] == "article" and q["useProxy"] == "none"
    assert q["naturalLanguage"] == "entities,summary"


def test_extract_option_validation():
    with pytest.raises(DiffbotError, match="fields"):
        list(ExtractTool.from_credentials(CREDS).invoke({"url": "https://example.org", "fields": "a&token=b"}))
    with pytest.raises(DiffbotError, match="timeout"):
        list(ExtractTool.from_credentials(CREDS).invoke({"url": "https://example.org", "timeout": 5}))


def test_extract_rejects_unknown_option_values():
    with pytest.raises(DiffbotError, match="mode"):
        list(ExtractTool.from_credentials(CREDS).invoke({"url": "https://example.org", "mode": "bogus"}))
    with pytest.raises(DiffbotError, match="natural_language"):
        list(ExtractTool.from_credentials(CREDS).invoke({"url": "https://example.org", "natural_language": "x"}))


def test_extract_passes_options_to_sdks_that_support_them():
    calls = []

    class Fake:
        token = TOKEN

        def extract(self, url, api="analyze", fmt="markdown", *, mode=None, fields=None, timeout=None):
            calls.append((url, api, fmt, mode, fields, timeout))
            return {"objects": []}

    sdk.extract(Fake(), "https://x.org", "article", "json", {"mode": "llm", "fields": ["links"], "timeout": 5000})  # type: ignore[arg-type]
    assert calls == [("https://x.org", "article", "json", "llm", ["links"], 5000)]


# ------------------------------------------------------------ KG / search limits


def test_kg_offset_and_large_size_are_sent(serve):
    seen = serve(lambda r: httpx.Response(200, json={"hits": 0, "data": []}))
    list(SearchOrganizationsTool.from_credentials(CREDS).invoke({"name": "Diffbot", "size": 100, "offset": 200}))
    body = json.loads(seen[0].content)
    assert body["size"] == 100 and body["from"] == 200


def test_web_search_allows_50_results_and_rejects_more(serve):
    seen = serve(lambda r: httpx.Response(200, json={"search_results": []}))
    list(SearchWebTool.from_credentials(CREDS).invoke({"query": "x", "num_results": 50, "max_tokens": 32000}))
    assert seen[0].url.params["size"] == "50"
    with pytest.raises(DiffbotError):
        list(SearchWebTool.from_credentials(CREDS).invoke({"query": "x", "num_results": 51}))


# ------------------------------------------------------------ crawl


def test_crawl_start_never_watches_and_returns_the_job_name(serve):
    seen = serve(lambda r: httpx.Response(200, json={}))
    payload = _json(
        list(CrawlStartTool.from_credentials(CREDS).invoke({"seeds": "example.org", "job_name": "j1", "hops": 1}))
    )
    assert payload["job_name"] == "j1"
    assert len(seen) == 1  # create only: no status poll, no data fetch
    assert seen[0].url.params["seeds"] == "https://example.org"
    assert seen[0].url.params["maxHops"] == "1"


@pytest.mark.parametrize("seeds", ["http://127.0.0.1", "https://ok.example.org localhost"])
def test_crawl_start_guards_seeds(seeds):
    with pytest.raises(DiffbotError, match="not allowed"):
        list(CrawlStartTool.from_credentials(CREDS).invoke({"seeds": seeds}))


def test_crawl_start_rejects_job_names_over_30_characters(serve):
    seen = serve(lambda r: httpx.Response(200, json={}))
    with pytest.raises(DiffbotError, match="30 characters"):
        list(CrawlStartTool.from_credentials(CREDS).invoke({"seeds": "example.org", "job_name": "j" * 31}))
    assert seen == []
    payload = _json(list(CrawlStartTool.from_credentials(CREDS).invoke({"seeds": "example.org", "job_name": "j" * 30})))
    assert payload["job_name"] == "j" * 30


def test_crawl_results_not_truncated_when_rows_fit(serve):
    serve(lambda r: httpx.Response(200, json=[{"title": "a"}, {"title": "b"}]))
    payload = _json(_jobs({"action": "results", "job_name": "j1", "limit": 2}))
    assert payload["returned"] == 2 and payload["truncated"] is False


def test_crawl_start_guards_api_url():
    with pytest.raises(DiffbotError, match="not allowed"):
        list(CrawlStartTool.from_credentials(CREDS).invoke({"seeds": "example.org", "api_url": "http://localhost/x"}))


def _jobs(parameters):
    return list(CrawlJobsTool.from_credentials(CREDS).invoke(parameters))


def test_crawl_jobs_list_and_status(serve):
    job = {"name": "j1", "jobStatus": {"status": 9, "message": "done"}, "objectsFound": 4, "secretish": "x"}
    serve(lambda r: httpx.Response(200, json={"jobs": [job]}))
    assert _json(_jobs({"action": "list"}))["jobs"][0]["name"] == "j1"
    status = _json(_jobs({"action": "status", "job_name": "j1"}))["job"]
    assert status["objectsFound"] == 4 and "secretish" not in status


def test_crawl_jobs_status_for_missing_job(serve):
    serve(lambda r: httpx.Response(200, json={"jobs": []}))
    with pytest.raises(DiffbotError, match="not find"):
        _jobs({"action": "status", "job_name": "nope"})


def test_crawl_results_fall_back_to_the_data_endpoint_and_parse_csv(serve):
    csv_text = 'Url,Crawl Status\nhttps://a.example.org,Success\nhttps://b.example.org,Success\n'
    seen = serve(lambda r: httpx.Response(200, text=csv_text))
    payload = _json(_jobs({"action": "results", "job_name": "j1", "result_type": "urls", "limit": 1}))
    assert seen[0].url.path == "/v3/crawl/data"
    assert seen[0].url.params["type"] == "urls"
    assert seen[0].url.params["num"] == "2"  # one extra row detects truncation
    assert payload["returned"] == 1 and payload["truncated"] is True
    assert payload["results"][0]["Url"] == "https://a.example.org"


def test_crawl_results_use_native_crawl_download_when_available():
    class Fake:
        token = TOKEN

        def crawl_download(self, name, *, format="json", type=None, num=None):
            return httpx.Response(200, json=[{"title": "t"}])

    assert sdk.crawl_download(Fake(), "j", num=5) == [{"title": "t"}]  # type: ignore[arg-type]


def test_crawl_download_job_error_shows_the_reason(serve):
    serve(lambda r: httpx.Response(200, json={"errorCode": 500, "error": "No collection record"}))
    with pytest.raises(DiffbotError, match="No collection record"):
        _jobs({"action": "results", "job_name": "j1"})


def test_crawl_delete_is_not_retried(serve):
    seen = serve(lambda r: httpx.Response(503, json={"message": "down"}))
    with pytest.raises(DiffbotError):
        _jobs({"action": "delete", "job_name": "j1"})
    assert len(seen) == 1
    assert seen[0].url.params["delete"] == "1"


def test_crawl_delete_is_labelled_destructive():
    spec = yaml.safe_load(open("diffbot/tools/crawl_jobs.yaml"))
    assert "destructive" in spec["description"]["human"]["en_US"].lower()
    action = next(p for p in spec["parameters"] if p["name"] == "action")
    assert "destructive" in action["human_description"]["en_US"].lower()


def test_all_tool_yamls_are_registered_and_exist():
    provider = yaml.safe_load(open("diffbot/provider/diffbot.yaml"))
    for path in provider["tools"]:
        spec = yaml.safe_load(open(f"diffbot/{path}"))
        assert spec["extra"]["python"]["source"].startswith("tools/")
    assert {"tools/crawl_start.yaml", "tools/crawl_jobs.yaml"} <= set(provider["tools"])
