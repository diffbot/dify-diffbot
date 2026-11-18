"""Tool and credential tests with a mocked HTTP session. No live Diffbot calls."""

import json

import httpx
import pytest

from provider.diffbot import DiffbotProvider
from tools.client import TOKEN_PATTERN, DiffbotError
from tools.extract import ExtractTool
from tools.resolve_entities import ResolveEntitiesTool
from tools.search_news import SearchNewsTool
from tools.search_organizations import SearchOrganizationsTool
from tools.search_people import SearchPeopleTool
from tools.search_web import SearchWebTool

TOKEN = "a" * 32
assert TOKEN_PATTERN.fullmatch(TOKEN)


class FakeResponse:
    """(status, payload) pair a responder returns; converted to an httpx.Response."""

    def __init__(self, status_code, payload, headers=None):
        self.status_code = status_code
        self.payload = payload
        self.headers = headers or {}


@pytest.fixture
def session_factory(monkeypatch):
    """Serve every SDK request from ``responder(method, url, kwargs)`` via httpx.MockTransport.

    ``kwargs`` has ``params`` (query dict), ``headers`` and ``json`` (parsed body), so the
    real SDK client and the plugin's host guard run; only the socket is replaced.
    """
    holder = {"calls": []}

    def install(responder):
        def handler(request: httpx.Request) -> httpx.Response:
            kwargs = {
                "params": dict(request.url.params),
                "headers": dict(request.headers),
                "json": json.loads(request.content) if request.content else None,
            }
            url = str(request.url.copy_with(query=None))
            holder["calls"].append({"method": request.method, "url": url, **kwargs})
            result = responder(request.method, url, kwargs)
            if isinstance(result.payload, str):
                return httpx.Response(result.status_code, text=result.payload, headers=result.headers)
            return httpx.Response(result.status_code, json=result.payload, headers=result.headers)

        monkeypatch.setattr("tools.sdk.httpx.HTTPTransport", lambda **_: httpx.MockTransport(handler))
        return holder

    return install


def _json_message(messages):
    json_messages = [item for item in messages if item.type.value == "json"]
    assert json_messages, messages
    return json_messages[-1].message.json_object


def _text(messages):
    return "\n".join(item.message.text for item in messages if item.type.value == "text")


def test_credential_validation_uses_account_api_and_hides_the_token(session_factory):
    def responder(method, url, kwargs):
        assert kwargs["params"]["token"] == TOKEN
        assert kwargs["params"]["days"] == "1"
        return FakeResponse(200, {"plan": "FREE", "status": "active", "token": TOKEN, "email": "hidden@example.com"})

    session_factory(responder)
    DiffbotProvider()._validate_credentials({"diffbot_token": TOKEN})


def test_credential_validation_rejects_unauthorized_without_echoing_the_token(session_factory):
    def responder(method, url, kwargs):
        return FakeResponse(401, {"errorCode": 401, "error": f"bad token {TOKEN}"})

    session_factory(responder)
    with pytest.raises(Exception) as caught:
        DiffbotProvider()._validate_credentials({"diffbot_token": TOKEN})
    assert TOKEN not in str(caught.value)
    assert "Invalid or unauthorized" in str(caught.value)


def test_web_search_uses_bearer_auth_and_not_the_query_token(session_factory):
    def responder(method, url, kwargs):
        assert url.endswith("/api/v1/web_search")
        assert kwargs["headers"]["authorization"] == f"Bearer {TOKEN}"
        assert "token" not in (kwargs.get("params") or {})
        assert kwargs["params"]["text"] == "hypothyroidism"
        assert "snippetLength" not in kwargs["params"]  # API default applies
        return FakeResponse(
            200,
            {
                "query": ["hypothyroidism"],
                "timeMs": 12,
                "search_results": [
                    {
                        "score": 0.91,
                        "title": "Guideline",
                        "pageUrl": "https://example.org/guide",
                        "date": "Mon, 01 Jan 2024 00:00:00 GMT",
                        "content": "A passage.",
                    }
                ],
            },
        )

    session_factory(responder)
    tool = SearchWebTool.from_credentials({"diffbot_token": TOKEN})
    messages = list(tool.invoke({"query": "hypothyroidism", "num_results": 2}))
    payload = _json_message(messages)
    assert payload["results"][0]["pageUrl"] == "https://example.org/guide"
    assert "Guideline" in _text(messages)


def test_url_lookup_defaults_to_full_snippet(session_factory):
    def responder(method, url, kwargs):
        assert kwargs["params"]["snippetLength"] == "FULL"
        assert kwargs["params"]["rerank"] == "none"
        return FakeResponse(200, {"search_results": []})

    session_factory(responder)
    tool = SearchWebTool.from_credentials({"diffbot_token": TOKEN})
    list(tool.invoke({"query": "url:https://example.org/paper"}))


def test_extract_calls_analyze_and_truncates_text(session_factory):
    def responder(method, url, kwargs):
        assert url.endswith("/v3/analyze")
        assert kwargs["params"]["mode"] == "llm"
        assert kwargs["params"]["token"] == TOKEN
        return FakeResponse(
            200,
            {
                "objects": [
                    {
                        "type": "article",
                        "title": "Story",
                        "pageUrl": "https://example.org/story",
                        "text": "x" * 9000,
                        "html": "<p>secret markup</p>",
                    }
                ]
            },
        )

    session_factory(responder)
    tool = ExtractTool.from_credentials({"diffbot_token": TOKEN})
    payload = _json_message(list(tool.invoke({"url": "https://example.org/story", "page_type": "auto"})))
    assert payload["objects"][0]["title"] == "Story"
    assert len(payload["objects"][0]["text"]) < 9000
    assert "html" not in payload["objects"][0]


def test_extract_reports_api_error_without_the_token(session_factory):
    def responder(method, url, kwargs):
        return FakeResponse(200, {"errorCode": 500, "error": f"render failed for token {TOKEN}"})

    session_factory(responder)
    tool = ExtractTool.from_credentials({"diffbot_token": TOKEN})
    with pytest.raises(DiffbotError) as caught:
        list(tool.invoke({"url": "https://example.org/story"}))
    assert TOKEN not in str(caught.value)


def test_organization_search_drops_unexpected_contact_fields(session_factory):
    def responder(method, url, kwargs):
        assert "kg.diffbot.com" in url
        assert "type:Organization" in kwargs["json"]["query"]
        assert 'name:"Diffbot"' in kwargs["json"]["query"]
        return FakeResponse(
            200,
            {
                "hits": 1,
                "data": [
                    {
                        "entity": {
                            "name": "Diffbot",
                            "homepageUri": "https://www.diffbot.com",
                            "nbEmployees": 100,
                            "emailAddresses": ["private@example.com"],
                            "phoneNumbers": ["+1-555-0100"],
                            "location": {"city": {"name": "Menlo Park"}, "country": {"name": "United States"}},
                            "id": "abc123",
                        }
                    }
                ],
            },
        )

    session_factory(responder)
    tool = SearchOrganizationsTool.from_credentials({"diffbot_token": TOKEN})
    payload = _json_message(list(tool.invoke({"name": "Diffbot", "size": 5})))
    record = payload["results"][0]
    assert record["name"] == "Diffbot"
    assert record["location"]["city"] == "Menlo Park"
    assert "emailAddresses" not in record
    assert "phoneNumbers" not in record
    assert "private@example.com" not in json.dumps(payload)


def test_people_search_keeps_employment_and_drops_email(session_factory):
    def responder(method, url, kwargs):
        assert "type:Person" in kwargs["json"]["query"]
        return FakeResponse(
            200,
            {
                "hits": 1,
                "data": [
                    {
                        "entity": {
                            "name": "Ada Lovelace",
                            "emailAddresses": [{"contactString": "ada@example.com"}],
                            "employments": [
                                {"title": "Engineer", "isCurrent": True, "employer": {"name": "Analytical Engines"}}
                            ],
                            "diffbotUri": "http://diffbot.com/entity/person1",
                        }
                    }
                ],
            },
        )

    session_factory(responder)
    tool = SearchPeopleTool.from_credentials({"diffbot_token": TOKEN})
    payload = _json_message(list(tool.invoke({"name": "Ada Lovelace"})))
    record = payload["results"][0]
    assert record["employments"][0]["employer"] == "Analytical Engines"
    assert record["id"] == "person1"
    assert "ada@example.com" not in json.dumps(payload)


def test_news_search_passes_the_built_query(session_factory):
    seen = {}

    def responder(method, url, kwargs):
        seen["query"] = kwargs["json"]["query"]
        return FakeResponse(
            200,
            {
                "hits": 1,
                "data": [
                    {
                        "entity": {
                            "title": "Launch",
                            "siteName": "Reuters",
                            "date": {"str": "d2024-05-01"},
                            "pageUrl": "https://example.org/launch",
                            "html": "<p>full html</p>",
                        }
                    }
                ],
            },
        )

    session_factory(responder)
    tool = SearchNewsTool.from_credentials({"diffbot_token": TOKEN})
    payload = _json_message(list(tool.invoke({"title": "Launch", "include_text": False})))
    assert 'title:"Launch"' in seen["query"]
    assert seen["query"].endswith(" sortBy:date")
    assert "revSortBy" not in seen["query"]
    assert payload["results"][0]["date"] == "d2024-05-01"
    assert "html" not in payload["results"][0]
    assert "text" not in payload["results"][0]


def test_resolve_entities_builds_a_dql_filter(session_factory):
    def responder(method, url, kwargs):
        assert method == "POST"
        assert "nl.diffbot.com" in url
        assert kwargs["json"][0]["content"] == "Diffbot is in Menlo Park."
        assert kwargs["params"]["fields"] == "entities,sentiment"
        return FakeResponse(
            200,
            [
                {
                    "sentiment": 0.1,
                    "entities": [
                        {
                            "name": "Diffbot",
                            "allTypes": [{"name": "organization"}],
                            "confidence": 0.9,
                            "salience": 0.8,
                            "sentiment": 0.2,
                            "diffbotUri": "http://diffbot.com/entity/org1",
                            "mentions": [{"text": "Diffbot"}],
                        },
                        {"name": "Menlo Park", "allTypes": [{"name": "location"}], "mentions": []},
                    ],
                }
            ],
        )

    session_factory(responder)
    tool = ResolveEntitiesTool.from_credentials({"diffbot_token": TOKEN})
    payload = _json_message(list(tool.invoke({"text": "Diffbot is in Menlo Park."})))
    assert payload["entities"][0]["id"] == "org1"
    assert payload["dql_filter"] == 'id:or("org1")'
    assert payload["entities"][1]["id"] is None


def test_timeout_becomes_a_safe_error(session_factory):
    def responder(method, url, kwargs):
        raise httpx.ReadTimeout("timed out with token " + TOKEN)

    session_factory(responder)
    tool = SearchWebTool.from_credentials({"diffbot_token": TOKEN})
    with pytest.raises(DiffbotError) as caught:
        list(tool.invoke({"query": "diffbot"}))
    assert TOKEN not in str(caught.value)
    assert "timed out" in str(caught.value).lower()
