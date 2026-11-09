"""HTTP client for the Diffbot APIs used by this plugin.

Authentication is a Diffbot token. Extract, Knowledge Graph, Enhance, Account,
and Natural Language calls send it as the ``token`` query parameter. Web Search
on ``llm.diffbot.com`` uses ``Authorization: Bearer`` instead, which is what
the current Web Search reference documents.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

import requests

ACCOUNT_URL = "https://api.diffbot.com/v4/account"
EXTRACT_BASE = "https://api.diffbot.com/v3"
WEB_SEARCH_URL = "https://llm.diffbot.com/api/v1/web_search"
DQL_URL = "https://kg.diffbot.com/kg/v3/dql"
ENHANCE_URL = "https://kg.diffbot.com/kg/v3/enhance"
NLP_URL = "https://nl.diffbot.com/v1/"

TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9._~+\-]{16,256}$")
BLOCKED_HOST_SUFFIXES = (".local", ".localhost", ".internal")
BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata.google",
}

TIMEOUTS = {
    "account": 15,
    "search": 30,
    "extract": 45,
    "dql": 30,
    "enhance": 30,
    "nlp": 30,
}


class DiffbotError(Exception):
    """A safe, user-facing Diffbot failure. Messages never include the token."""


class DiffbotClient:
    def __init__(self, token: str, session: requests.Session | None = None) -> None:
        self.token = normalize_token(token)
        self.session = session or requests.Session()

    def validate_token(self) -> None:
        """Confirm the token with the Account API without returning account details.

        ``days=1`` keeps the usage history small. The response body contains the
        token itself, so this method returns nothing and callers must not log it.
        """
        data = self._request_json(
            "GET",
            ACCOUNT_URL,
            params={"token": self.token, "days": 1},
            timeout=TIMEOUTS["account"],
        )
        if not isinstance(data, dict):
            raise DiffbotError("Diffbot account check returned an unexpected response.")
        if not any(key in data for key in ("plan", "status", "email", "name")):
            raise DiffbotError("Diffbot account check did not return account details.")

    def web_search(
        self,
        query: str,
        *,
        num_results: int,
        snippet_length: str,
        max_tokens: int | None,
        rerank: str | None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "text": query,
            "size": num_results,
            "snippetLength": snippet_length.upper(),
        }
        if max_tokens is not None:
            params["maxTokens"] = max_tokens
        if rerank:
            params["rerank"] = rerank
        data = self._request_json(
            "GET",
            WEB_SEARCH_URL,
            params=params,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
            timeout=TIMEOUTS["search"],
        )
        if not isinstance(data, dict):
            raise DiffbotError("Diffbot web search returned an unexpected response.")
        return data

    def extract(self, url: str, *, page_type: str, markdown: bool) -> dict[str, Any]:
        endpoint = "analyze" if page_type == "auto" else page_type
        params: dict[str, Any] = {
            "token": self.token,
            "url": url,
            "timeout": 30000,
        }
        if markdown:
            params["mode"] = "llm"
        data = self._request_json(
            "GET",
            f"{EXTRACT_BASE}/{endpoint}",
            params=params,
            timeout=TIMEOUTS["extract"],
        )
        if not isinstance(data, dict):
            raise DiffbotError("Diffbot extract returned an unexpected response.")
        return data

    def dql(self, query: str, *, size: int) -> dict[str, Any]:
        data = self._request_json(
            "GET",
            DQL_URL,
            params={"token": self.token, "query": query, "size": size},
            timeout=TIMEOUTS["dql"],
        )
        if not isinstance(data, dict):
            raise DiffbotError("Diffbot Knowledge Graph search returned an unexpected response.")
        return data

    def enhance(self, params: dict[str, Any]) -> dict[str, Any]:
        data = self._request_json(
            "GET",
            ENHANCE_URL,
            params={"token": self.token, **params},
            timeout=TIMEOUTS["enhance"],
        )
        if not isinstance(data, dict):
            raise DiffbotError("Diffbot Enhance returned an unexpected response.")
        return data

    def resolve_entities(self, text: str, *, lang: str) -> dict[str, Any]:
        data = self._request_json(
            "POST",
            NLP_URL,
            params={"token": self.token, "fields": "entities,sentiment"},
            json_body=[{"lang": lang, "format": "plain text", "content": text}],
            timeout=TIMEOUTS["nlp"],
        )
        if isinstance(data, list):
            data = data[0] if data else {}
        if not isinstance(data, dict):
            raise DiffbotError("Diffbot entity resolution returned an unexpected response.")
        return data

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        timeout: float,
    ) -> Any:
        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=timeout,
            )
        except requests.Timeout as exc:
            raise DiffbotError("The Diffbot request timed out.") from exc
        except requests.RequestException as exc:
            raise DiffbotError("The Diffbot request failed before a response was received.") from exc

        if response.status_code in (401, 403):
            raise DiffbotError("Invalid or unauthorized Diffbot token.")
        if response.status_code == 429:
            raise DiffbotError("Diffbot rate limit exceeded. Retry later.")
        if response.status_code >= 400:
            raise DiffbotError(
                f"Diffbot API error {response.status_code}: {self._safe_body_message(response)}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise DiffbotError("Diffbot returned a non-JSON response.") from exc

        if isinstance(data, dict) and data.get("errorCode"):
            message = str(data.get("error") or data.get("message") or "request failed")
            lowered = message.lower()
            if "token" in lowered or "authorized" in lowered or "unauthor" in lowered:
                raise DiffbotError("Invalid or unauthorized Diffbot token.")
            raise DiffbotError(f"Diffbot request failed: {self._redact(message)}")
        return data

    def _safe_body_message(self, response: requests.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return "request failed"
        if isinstance(data, dict):
            message = str(data.get("error") or data.get("message") or "request failed")
            return self._redact(message)[:300]
        return "request failed"

    def _redact(self, text: str) -> str:
        if self.token and self.token in text:
            text = text.replace(self.token, "[redacted]")
        return text


def normalize_token(raw: str) -> str:
    if not isinstance(raw, str):
        raise DiffbotError("Diffbot token is required.")
    cleaned = raw.strip()
    if not cleaned:
        raise DiffbotError("Diffbot token is required.")
    if not TOKEN_PATTERN.fullmatch(cleaned):
        raise DiffbotError(
            "Diffbot token format is invalid. Paste the token from app.diffbot.com without spaces."
        )
    return cleaned


def validate_public_http_url(url: str) -> str:
    """Allow only http(s) URLs whose host is not an obvious local or metadata target.

    Diffbot fetches the page. This check stops the plugin from asking Diffbot to
    call loopback, link-local, or private literal addresses.
    """
    if not isinstance(url, str):
        raise DiffbotError("A page URL is required.")
    url = url.strip()
    if not url:
        raise DiffbotError("A page URL is required.")
    if len(url) > 2048:
        raise DiffbotError("URL is too long.")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise DiffbotError("URL must start with http:// or https://.")
    if parsed.username or parsed.password:
        raise DiffbotError("URL must not include a username or password.")
    host = (parsed.hostname or "").rstrip(".").lower()
    if not host:
        raise DiffbotError("URL must include a host.")
    if host in BLOCKED_HOSTS or host.endswith(BLOCKED_HOST_SUFFIXES):
        raise DiffbotError("URL host is not allowed.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        raise DiffbotError("URL host is not allowed.")
    return url
