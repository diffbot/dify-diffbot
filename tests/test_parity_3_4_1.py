"""Plugin parity with diffbot 3.4.1: new tools, crawl flags, endpoint overrides, ontology cache.

All HTTP is served by httpx.MockTransport; no live Diffbot calls.
"""

import json
import threading

import httpx
import pytest

from provider.diffbot import DiffbotProvider
from tools import ontology_cache, sdk
from tools.account_usage import AccountUsageTool
from tools.ask import AskTool
from tools.client import DiffbotError
from tools.crawl_start import CrawlStartTool
from tools.extract import ExtractTool
from tools.kg_ontology import KgOntologyTool
from tools.kg_query import KgQueryTool
from tools.nlp import NlpTool
from tools.search_news import SearchNewsTool
from tools.search_organizations import SearchOrganizationsTool
from tools.search_people import SearchPeopleTool
from tools.search_web import SearchWebTool

TOKEN = "a" * 32
CREDS = {"diffbot_token": TOKEN}

ONTOLOGY = {
    "types": {"Organization": {"fields": {"name": {"type": "String"}, "oldField": {"type": "String", "isDeprecated": True}}}},
    "composites": {"Location": {"fields": {"city": {"type": "LinkedEntity", "leType": ["Place"]}}}},
    "enums": {"Language": {"values": ["en", "fr"]}},
    "taxonomies": {
        "OrganizationCategory": {
            "categories": [{"name": "Software Companies", "children": [{"name": "Enterprise Software Companies"}]}]
        }
    },
}


@pytest.fixture
def serve(monkeypatch):
    seen: list[httpx.Request] = []

    def install(handler):
        def wrapped(request):
            seen.append(request)
            return handler(request)

        monkeypatch.setattr("tools.sdk.httpx.HTTPTransport", lambda **_: httpx.MockTransport(wrapped))
        return seen

    return install


@pytest.fixture(autouse=True)
def fresh_ontology_cache():
    ontology_cache.CACHE.clear()
    yield
    ontology_cache.CACHE.clear()


def _json(messages):
    return [m for m in messages if m.type.value == "json"][-1].message.json_object


def run(tool_cls, params, creds=CREDS):
    return list(tool_cls.from_credentials(creds).invoke(params))


def _body(request):
    return json.loads(request.content)


# ------------------------------------------------------------ kg_query


def test_kg_query_sends_wire_names_and_offset_as_from(serve):
    seen = serve(lambda r: httpx.Response(200, json={"hits": 1, "data": []}))
    run(KgQueryTool, {
        "query": "type:Organization", "size": 7, "offset": 3, "type": "text", "col": "name", "filter": "a",
        "filter_exclude": "b", "jsonmode": "id", "non_canonical_facts": True, "no_dedup_articles": True,
        "cluster": "best", "exportfile": "ignored",
    })
    body = _body(seen[0])
    assert seen[0].method == "POST" and seen[0].url.path == "/kg/v3/dql"
    assert body["size"] == 7 and body["from"] == 3
    assert body["filterExclude"] == "b" and body["filter"] == "a"
    assert body["nonCanonicalFacts"] is True and body["noDedupArticles"] is True
    assert body["jsonmode"] == "id" and body["cluster"] == "best" and body["type"] == "text" and body["col"] == "name"
    assert "exportfile" not in body  # blob file name only, never a server-side name
    assert "token" not in body


def test_kg_query_count_only_sends_size_zero_and_returns_hits_only(serve):
    seen = serve(lambda r: httpx.Response(200, json={"hits": 42, "data": [{"name": "x"}]}))
    payload = _json(run(KgQueryTool, {"query": "type:Organization", "count_only": True, "size": 50}))
    assert _body(seen[0])["size"] == 0
    assert payload["hits"] == 42 and "data" not in payload and "results" not in payload


@pytest.mark.parametrize("tool,params", [
    (SearchOrganizationsTool, {"name": "Diffbot"}),
    (SearchPeopleTool, {"name": "Ada"}),
    (SearchNewsTool, {"mentions": "Diffbot"}),
])
def test_template_tools_count_only(serve, tool, params):
    seen = serve(lambda r: httpx.Response(200, json={"hits": 9, "data": [{"name": "x"}]}))
    payload = _json(run(tool, {**params, "count_only": True}))
    assert _body(seen[0])["size"] == 0
    assert payload["hits"] == 9 and "results" not in payload


def test_kg_query_scrubs_contact_fields_and_html_recursively(serve):
    entity = {
        "name": "Acme", "emailAddresses": [{"value": "a@b.com"}], "html": "<p>x</p>",
        "nested": {"phoneNumbers": ["+1"], "Emails": ["x@y.z"], "keep": 1},
        "list": [{"phone": "1", "ok": True}],
    }
    serve(lambda r: httpx.Response(200, json={"hits": 1, "data": [{"entity": entity}]}))
    payload = _json(run(KgQueryTool, {"query": "type:Organization"}))
    text = json.dumps(payload)
    for leaked in ("a@b.com", "<p>", "+1", "x@y.z", "emailAddresses", "phoneNumbers"):
        assert leaked not in text
    assert payload["data"][0]["entity"]["nested"] == {"keep": 1}
    assert payload["data"][0]["entity"]["list"] == [{"ok": True}]


def test_kg_query_scrubs_jsonl(serve):
    lines = "\n".join(json.dumps({"name": n, "emails": ["a@b.c"]}) for n in ("a", "b"))
    serve(lambda r: httpx.Response(200, text=lines))
    payload = _json(run(KgQueryTool, {"query": "type:Organization", "format": "jsonl"}))
    assert payload["returned"] == 2 and "emails" not in json.dumps(payload)


def test_kg_query_caps_output_and_flags_truncation(serve, monkeypatch):
    monkeypatch.setattr("tools.kg_query.OUTPUT_LIMIT", 100)
    rows = [{"entity": {"name": "n" * 40}} for _ in range(10)]
    serve(lambda r: httpx.Response(200, json={"hits": 10, "data": rows}))
    payload = _json(run(KgQueryTool, {"query": "type:Organization"}))
    assert payload["truncated"] is True and payload["returned"] < 10


@pytest.mark.parametrize("fmt,content,mime", [
    ("csv", "a,b\n1,2\n", "text/csv"),
    ("xlsx", b"PK\x03\x04bytes", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ("xls", b"\xd0\xcf\x11bytes", "application/vnd.ms-excel"),
])
def test_kg_query_exports_are_blob_files(serve, fmt, content, mime):
    seen = serve(lambda r: httpx.Response(200, content=content if isinstance(content, bytes) else content.encode()))
    messages = run(KgQueryTool, {"query": "type:Organization", "format": fmt, "exportfile": "orgs"})
    blob = next(m for m in messages if m.type.value == "blob")
    assert blob.message.blob == (content if isinstance(content, bytes) else content.encode())
    assert blob.meta["mime_type"] == mime and blob.meta["filename"] == f"orgs.{fmt}"
    assert _body(seen[0])["format"] == fmt
    assert _json(messages)["scrubbed"] is False


def test_kg_query_validation(serve):
    serve(lambda r: httpx.Response(200, json={}))
    with pytest.raises(DiffbotError, match="too long"):
        run(KgQueryTool, {"query": "x" * 10_001})
    with pytest.raises(DiffbotError, match="format"):
        run(KgQueryTool, {"query": "x", "format": "xml"})
    with pytest.raises(DiffbotError, match="csv"):
        run(KgQueryTool, {"query": "x", "exportseparator": ";"})
    with pytest.raises(DiffbotError):
        run(KgQueryTool, {"query": "x", "size": 101})


# ------------------------------------------------------------ crawl flags and options


def test_crawl_tri_state_flags_are_absent_by_default_and_zero_only_for_off(serve):
    seen = serve(lambda r: httpx.Response(200, json={}))
    run(CrawlStartTool, {"seeds": "example.org", "job_name": "j"})
    params = seen[0].url.params
    for wire in ("obeyRobots", "useProxies", "useCanonical"):
        assert wire not in params
    run(CrawlStartTool, {"seeds": "example.org", "job_name": "j", "obey_robots_mode": "off",
                         "use_proxies_mode": "off", "use_canonical_mode": "on"})
    params = seen[1].url.params
    assert params["obeyRobots"] == "0" and params["useProxies"] == "0" and params["useCanonical"] == "1"
    run(CrawlStartTool, {"seeds": "example.org", "job_name": "j", "obey_robots_mode": "on"})
    assert seen[2].url.params["obeyRobots"] == "1"


def test_legacy_boolean_crawl_values_do_not_change_robots_behavior(serve):
    seen = serve(lambda r: httpx.Response(200, json={}))
    run(CrawlStartTool, {"seeds": "example.org", "job_name": "j", "obey_robots": False, "use_proxies": False})
    assert "obeyRobots" not in seen[0].url.params and "useProxies" not in seen[0].url.params


def test_crawl_new_options_reach_the_wire(serve):
    seen = serve(lambda r: httpx.Response(200, json={}))
    run(CrawlStartTool, {
        "seeds": "example.org", "job_name": "j", "url_crawl_regex": "a.*", "url_process_regex": "b.*",
        "page_process_pattern": "<h1", "max_to_crawl_per_subdomain": 5, "max_to_process_per_subdomain": 6,
        "notify_webhook": "https://hooks.example.org/x", "notify_email": "me@example.org",
        "custom_headers": "X-A: 1\n\nX-B: 2",
    })
    params = seen[0].url.params
    assert params["urlCrawlRegEx"] == "a.*" and params["urlProcessRegEx"] == "b.*"
    assert params["pageProcessPattern"] == "<h1"
    assert params["maxToCrawlPerSubdomain"] == "5" and params["maxToProcessPerSubdomain"] == "6"
    assert params["notifyWebhook"] == "https://hooks.example.org/x" and params["notifyEmail"] == "me@example.org"
    assert params.get_list("customHeaders") == ["X-A: 1", "X-B: 2"]


@pytest.mark.parametrize("extra,match", [
    ({"notify_webhook": "http://localhost/x"}, "not allowed"),
    ({"notify_webhook": "ftp://example.org"}, "http"),
    ({"notify_email": "not-an-email"}, "email"),
    ({"job_name": "j" * 31}, "30 characters"),
])
def test_crawl_notify_and_name_validation(serve, extra, match):
    seen = serve(lambda r: httpx.Response(200, json={}))
    with pytest.raises(DiffbotError, match=match):
        run(CrawlStartTool, {"seeds": "example.org", **extra})
    assert seen == []


# ------------------------------------------------------------ ask


def _sse(*chunks):
    return "".join(f'data: {json.dumps({"choices": [{"delta": {"content": c}}]})}\n\n' for c in chunks)


def test_ask_streams_text_chunks_with_bearer_auth(serve):
    seen = serve(lambda r: httpx.Response(200, text=_sse("Hel", "lo")))
    messages = run(AskTool, {"question": "hi", "system_prompt": "be brief"})
    texts = [m.message.text for m in messages if m.type.value == "text"]
    assert texts == ["Hel", "lo"]
    assert _json(messages)["answer"] == "Hello"
    assert seen[0].headers["authorization"] == f"Bearer {TOKEN}"
    body = _body(seen[0])
    assert body["messages"][0] == {"role": "system", "content": "be brief"} and body["stream"] is True


def test_ask_without_stream_returns_one_text_message(serve):
    serve(lambda r: httpx.Response(200, text=_sse("a", "b")))
    texts = [m.message.text for m in run(AskTool, {"question": "hi", "stream": False}) if m.type.value == "text"]
    assert texts == ["ab"]


def test_ask_json_schema_uses_json_schema_response_format(serve):
    seen = serve(lambda r: httpx.Response(200, text=_sse('{"city": "Paris"}')))
    schema = {"type": "object", "properties": {"city": {"type": "string"}}}
    payload = _json(run(AskTool, {"question": "capital?", "output": "json_schema", "json_schema": json.dumps(schema)}))
    assert payload["answer"] == {"city": "Paris"}
    fmt = _body(seen[0])["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["schema"] == schema


def test_ask_json_never_sends_bare_json_object(serve):
    seen = serve(lambda r: httpx.Response(200, text=_sse('{"a": 1}')))
    run(AskTool, {"question": "x", "output": "json"})
    assert _body(seen[0])["response_format"]["type"] == "json_schema"


def test_ask_invalid_json_answer_is_a_plain_message(serve):
    serve(lambda r: httpx.Response(200, text=_sse("not json at all")))
    with pytest.raises(DiffbotError, match="valid JSON") as caught:
        run(AskTool, {"question": "x", "output": "json"})
    assert "not json" not in str(caught.value)


@pytest.mark.parametrize("schema", ["{bad", "[1]", "x" * 20_001])
def test_ask_rejects_bad_schemas(serve, schema):
    seen = serve(lambda r: httpx.Response(200, text=_sse("x")))
    with pytest.raises(DiffbotError):
        run(AskTool, {"question": "x", "output": "json_schema", "json_schema": schema})
    assert seen == []


def test_ask_error_raised_mid_stream_is_redacted(serve):
    class Broken(httpx.SyncByteStream):
        def __iter__(self):
            yield _sse("partial").encode()
            raise httpx.ReadError(f"connection lost token={TOKEN} Bearer {TOKEN}")

    serve(lambda r: httpx.Response(200, stream=Broken()))
    with pytest.raises(DiffbotError) as caught:
        run(AskTool, {"question": "x"})
    assert TOKEN not in str(caught.value)


def test_ask_auth_failure_is_mapped(serve):
    serve(lambda r: httpx.Response(401, json={"error": f"bad {TOKEN}"}))
    with pytest.raises(DiffbotError, match="Invalid or unauthorized") as caught:
        run(AskTool, {"question": "x"})
    assert TOKEN not in str(caught.value)


def test_ask_question_cap():
    with pytest.raises(DiffbotError, match="too long"):
        run(AskTool, {"question": "q" * 8001})


# ------------------------------------------------------------ nlp, account


def test_nlp_sends_fields_summary_and_scrubs_records(serve):
    seen = serve(lambda r: httpx.Response(200, json=[{
        "sentiment": 0.1, "language": "en", "summary": "s",
        "facts": [{"value": "f", "emails": ["a@b.c"]}], "records": [{"phoneNumbers": ["1"], "name": "r"}],
        "entities": [],
    }]))
    payload = _json(run(NlpTool, {
        "text": "Hello", "fields": "facts, records,summary", "max_number_of_sentences": 2,
        "document_type": "article", "format": "plain text with title",
    }))
    assert seen[0].url.params["fields"] == "facts,records,summary"
    doc = _body(seen[0])[0]
    assert doc["customSummary"] == {"maxNumberOfSentences": 2}
    assert doc["documentType"] == "article" and doc["format"] == "plain text with title"
    assert "a@b.c" not in json.dumps(payload) and "phoneNumbers" not in json.dumps(payload)
    assert payload["records"] == [{"name": "r"}]


def test_nlp_validation():
    with pytest.raises(DiffbotError, match="too long"):
        run(NlpTool, {"text": "x" * 20_001})
    with pytest.raises(DiffbotError, match="fields"):
        run(NlpTool, {"text": "x", "fields": "bogus"})


def test_account_usage_returns_only_allowlisted_fields(serve):
    seen = serve(lambda r: httpx.Response(200, json={
        "plan": "FREE", "status": "active", "token": TOKEN, "childTokens": ["c" * 20], "email": "me@example.org",
        "usage": [{"date": "2026-11-01", "credits": 3, "token": TOKEN}],
    }))
    payload = _json(run(AccountUsageTool, {"days": 5}))
    assert seen[0].url.params["days"] == "5"
    assert payload["plan"] == "FREE" and payload["usage"] == [{"date": "2026-11-01", "credits": 3}]
    blob = json.dumps(payload) + "".join(m.message.text for m in run(AccountUsageTool, {}) if m.type.value == "text")
    assert TOKEN not in blob and "me@example.org" not in blob and "childTokens" not in blob


# ------------------------------------------------------------ endpoint overrides


@pytest.mark.parametrize("field,value,match", [
    ("kg_base", "http://kg.diffbot.com", "https"),
    ("kg_base", "https://127.0.0.1", "not allowed"),
    ("kg_base", "https://10.0.0.5", "not allowed"),
    ("kg_base", "https://localhost", "not allowed"),
    ("api_base", "https://example.com", "diffbot.com"),
    ("api_base", "https://diffbot.com.evil.example", "diffbot.com"),
    ("api_base", "https://notdiffbot.com", "diffbot.com"),
    ("llm_base", "https://user:pw@llm.diffbot.com", "username"),
    ("nlp_base", "https://nl.diffbot.com?x=1", "query"),
    ("nlp_base", "https://nl.diffbot.com#frag", "query"),
    ("api_base", "https://api.diffbot.com:8443", "port"),
])
def test_override_hosts_are_rejected(field, value, match):
    with pytest.raises(DiffbotError, match=match):
        sdk.make_client({**CREDS, field: value})


def test_override_hosts_accept_diffbot_subdomains_and_strip_trailing_slash():
    client = sdk.make_client({
        **CREDS, "kg_base": "https://kg-staging.diffbot.com/", "api_base": "https://diffbot.com", "llm_base": "  ",
        "nlp_base": "",
    })
    assert client.dql_url == "https://kg-staging.diffbot.com/kg/v3/dql"
    assert client.ontology_url == "https://kg-staging.diffbot.com/kg/ontology"
    assert client.account_url == "https://diffbot.com/v4/account"
    assert client.llm_url == "https://llm.diffbot.com/rag/v1/chat/completions"  # blank keeps the default
    assert client.nlp_url == "https://nl.diffbot.com/v1/"


def test_verify_token_follows_api_base(serve):
    seen = serve(lambda r: httpx.Response(200, json={"plan": "FREE"}))
    DiffbotProvider()._validate_credentials({**CREDS, "api_base": "https://api-staging.diffbot.com/"})
    assert seen[0].url.host == "api-staging.diffbot.com" and seen[0].url.path == "/v4/account"


def test_credential_validation_reports_a_bad_override_without_a_request(serve):
    seen = serve(lambda r: httpx.Response(200, json={}))
    with pytest.raises(Exception, match="diffbot.com"):
        DiffbotProvider()._validate_credentials({**CREDS, "api_base": "https://example.com"})
    assert seen == []


def test_override_reaches_the_tool_request(serve):
    seen = serve(lambda r: httpx.Response(200, json={"hits": 0, "data": []}))
    run(KgQueryTool, {"query": "x"}, {**CREDS, "kg_base": "https://kg-staging.diffbot.com"})
    assert seen[0].url.host == "kg-staging.diffbot.com"


# ------------------------------------------------------------ ontology


def _ontology_server(serve, counter):
    def handler(request):
        if request.url.path == "/kg/ontology":
            counter.append(request)
            return httpx.Response(200, json=ONTOLOGY)
        return httpx.Response(200, json={"hits": 0, "data": []})

    return serve(handler)


def test_ontology_is_fetched_once_across_tools_without_a_token(serve):
    fetches: list[httpx.Request] = []
    _ontology_server(serve, fetches)
    run(KgOntologyTool, {"lookup": "types"})
    run(KgOntologyTool, {"lookup": "enum_values", "name": "Language"})
    run(SearchOrganizationsTool, {"industry": "software companies"})
    assert len(fetches) == 1
    assert "token" not in fetches[0].url.params and "authorization" not in fetches[0].headers


def test_ontology_is_fetched_once_across_threads(serve):
    fetches: list[httpx.Request] = []
    _ontology_server(serve, fetches)
    errors = []

    def worker():
        try:
            run(KgOntologyTool, {"lookup": "taxonomies"})
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors and len(fetches) == 1


class FakeClient:
    def __init__(self, url, results):
        self.ontology_url = url
        self.results = results
        self.calls = 0

    def dql_fetch_ontology(self):
        self.calls += 1
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def test_ontology_cache_ttl_stale_on_failure_and_backoff():
    now = [0.0]
    cache = ontology_cache.OntologyCache(clock=lambda: now[0], ttl=100, backoff=10)
    first, second = object(), object()
    client = FakeClient("u1", [first, httpx.ConnectError("down"), second])
    assert cache.get(client) is first and cache.get(client) is first and client.calls == 1
    now[0] = 101  # expired; refresh fails -> stale copy, then back off
    assert cache.get(client) is first and client.calls == 2
    assert cache.get(client) is first and client.calls == 2
    now[0] = 112  # backoff over; refresh succeeds
    assert cache.get(client) is second and client.calls == 3


def test_ontology_cache_backs_off_after_failure_with_no_stale_copy_and_keys_by_url():
    now = [0.0]
    cache = ontology_cache.OntologyCache(clock=lambda: now[0], ttl=100, backoff=10)
    bad = FakeClient("u1", [httpx.ConnectError("down"), "ok"])
    with pytest.raises(httpx.ConnectError):
        cache.get(bad)
    with pytest.raises(DiffbotError, match="temporarily"):
        cache.get(bad)
    assert bad.calls == 1
    other = FakeClient("u2", ["other"])
    assert cache.get(other) == "other"  # a different URL has its own entry
    now[0] = 11
    assert cache.get(bad) == "ok"


def test_ontology_lookups(serve):
    _ontology_server(serve, [])
    assert _json(run(KgOntologyTool, {"lookup": "types"}))["names"] == ["Organization"]
    fields = _json(run(KgOntologyTool, {"lookup": "fields", "name": "Organization"}))["fields"]
    assert [f["name"] for f in fields] == ["name"]  # deprecated hidden
    fields = _json(run(KgOntologyTool, {"lookup": "fields", "name": "Organization", "include_deprecated": True}))["fields"]
    assert {f["name"] for f in fields} == {"name", "oldField"}
    values = _json(run(KgOntologyTool, {"lookup": "taxonomy_values", "name": "OrganizationCategory", "search": "enterprise"}))
    assert values["values"] == ["Enterprise Software Companies"]
    assert _json(run(KgOntologyTool, {"lookup": "find", "search": "enterprise"}))["names"] == ["Enterprise Software Companies"]
    with pytest.raises(DiffbotError, match="Not found"):
        run(KgOntologyTool, {"lookup": "fields", "name": "Nope"})


def test_ontology_search_is_literal_and_length_capped(serve):
    _ontology_server(serve, [])
    assert _json(run(KgOntologyTool, {"lookup": "find", "search": "(a+)+$["}))["names"] == []  # no regex error
    with pytest.raises(DiffbotError, match="too long"):
        run(KgOntologyTool, {"lookup": "find", "search": "x" * 201})


def test_ontology_raw_file_is_a_blob(serve):
    _ontology_server(serve, [])
    messages = run(KgOntologyTool, {"lookup": "raw_file"})
    blob = next(m for m in messages if m.type.value == "blob")
    assert json.loads(blob.message.blob)["enums"]["Language"]["values"] == ["en", "fr"]


# ------------------------------------------------------------ industry, web search, extract


def test_industry_resolves_case_insensitively_and_suggests_on_miss(serve):
    seen = _ontology_server(serve, [])
    run(SearchOrganizationsTool, {"industry": "software companies"})
    query = _body(seen[-1])["query"]
    assert 'categories.name:"Software Companies"' in query
    with pytest.raises(DiffbotError, match="Did you mean: .*Software Companies"):
        run(SearchOrganizationsTool, {"industry": "software company"})


def test_industry_passes_through_when_the_ontology_is_unavailable(serve):
    def handler(request):
        if request.url.path == "/kg/ontology":
            return httpx.Response(500, json={"message": "down"})
        return httpx.Response(200, json={"hits": 0, "data": []})

    seen = serve(handler)
    run(SearchOrganizationsTool, {"industry": "Whatever"})
    assert 'categories.name:"Whatever"' in _body(seen[-1])["query"]


def test_web_search_takes_up_to_five_queries_and_drops_blanks(serve):
    seen = serve(lambda r: httpx.Response(200, json={"search_results": []}))
    run(SearchWebTool, {"query": "a", "query_2": " ", "query_3": "c"})
    assert seen[0].url.params.get_list("text") == ["a", "c"]
    run(SearchWebTool, {"query": "a", "query_2": "b", "query_3": "c", "query_4": "d", "query_5": "e"})
    assert len(seen[1].url.params.get_list("text")) == 5
    with pytest.raises(DiffbotError, match="too long"):
        run(SearchWebTool, {"query": "a", "query_2": "x" * 2001})


def test_url_shortcut_applies_only_to_a_single_query(serve):
    seen = serve(lambda r: httpx.Response(200, json={"search_results": []}))
    run(SearchWebTool, {"query": "url:https://example.org/a"})
    assert seen[0].url.params["snippetLength"] == "FULL"
    run(SearchWebTool, {"query": "url:https://example.org/a", "query_2": "other"})
    assert "snippetLength" not in seen[1].url.params


def test_extract_supports_job_and_custom_api(serve):
    seen = serve(lambda r: httpx.Response(200, json={"objects": []}))
    run(ExtractTool, {"url": "https://example.org/j", "page_type": "job"})
    assert seen[0].url.path.endswith("/job")
    run(ExtractTool, {"url": "https://example.org/j", "custom_api": "my_api-2"})
    assert seen[1].url.path.endswith("/my_api-2")
    with pytest.raises(DiffbotError, match="custom_api"):
        run(ExtractTool, {"url": "https://example.org/j", "custom_api": "../x"})
