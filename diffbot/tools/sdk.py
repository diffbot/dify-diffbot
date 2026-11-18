"""Builds the Diffbot SDK client and adapts it to this plugin's policy.

The plugin runs on the ``diffbot`` Python SDK (sync ``Diffbot`` client). Everything
the SDK does not expose yet is reached through the public ``client.request()``
transport, never through private attributes, and each such helper feature-detects
the real method so it drops out when the SDK ships it:

* ``verify_token``     -> diffbot 3.3.0 (fallback: ``GET /v4/account?days=1``)
* ``crawl_download``   -> diffbot 3.3.0 (fallback: ``GET /v3/crawl/data``)
* extract options      -> diffbot 3.3.0 (fallback: ``GET /v3/{api}`` with the same params)

TODO: when diffbot 3.2.0 / 3.3.0 are released, pin ``diffbot`` in
``requirements.txt`` / ``pyproject.toml`` and delete the fallbacks.
"""

from __future__ import annotations

import csv
import inspect
import io
import json
import urllib.request
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any, cast

import httpx
from diffbot import (
    APIError,
    AuthError,
    Diffbot,
    DiffbotError as SdkError,
    ExtractionError,
    JobError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

from tools.client import (
    DiffbotError,
    check_public_host,
    normalize_token,
    redact,
)
from tools.sdk_types import CrawlJob, ExtractResponse

DEFAULT_TIMEOUT = 30.0
MIN_TIMEOUT = 5.0
MAX_TIMEOUT = 300.0  # dify_plugin's request ceiling is 300 s

INVALID_TOKEN = "Invalid or unauthorized Diffbot token."


class GuardedTransport(httpx.BaseTransport):
    """Wraps another transport and refuses private/loopback/metadata hosts and
    non-http(s) schemes before any socket is opened.

    With no ``inner`` transport it honors ``HTTP(S)_PROXY`` / ``ALL_PROXY`` /
    ``NO_PROXY`` like the old ``requests`` client did: httpx ignores the environment
    once an explicit transport is passed, which would break proxied Dify deployments.
    """

    def __init__(self, inner: httpx.BaseTransport | None = None) -> None:
        self._proxied: dict[str, httpx.BaseTransport] = {}
        if inner is None:
            proxies = urllib.request.getproxies()
            for scheme in ("http", "https"):
                proxy = proxies.get(scheme) or proxies.get("all")
                if proxy:
                    self._proxied[scheme] = httpx.HTTPTransport(proxy=proxy)
        self._inner = inner or httpx.HTTPTransport()

    def _transport_for(self, url: httpx.URL) -> httpx.BaseTransport:
        proxied = self._proxied.get(url.scheme)
        if proxied is None or urllib.request.proxy_bypass(url.host):
            return self._inner
        return proxied

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.scheme not in ("http", "https"):
            raise DiffbotError("Request scheme is not allowed.")
        check_public_host(request.url.host or "")
        return self._transport_for(request.url).handle_request(request)

    def close(self) -> None:
        self._inner.close()
        for transport in self._proxied.values():
            transport.close()


def parse_timeout(value: Any) -> float:
    if value is None or (isinstance(value, str) and not value.strip()):
        return DEFAULT_TIMEOUT
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        raise DiffbotError("Request timeout must be a number of seconds.") from None
    if not MIN_TIMEOUT <= seconds <= MAX_TIMEOUT:
        raise DiffbotError(f"Request timeout must be between {MIN_TIMEOUT:g} and {MAX_TIMEOUT:g} seconds.")
    return seconds


def make_client(credentials: Mapping[str, Any] | None, *, transport: httpx.BaseTransport | None = None) -> Diffbot:
    """Validate the credential form and return an SDK client behind the host guard."""
    credentials = credentials or {}
    raw = credentials.get("diffbot_token", "")
    token = normalize_token(raw if isinstance(raw, str) else "")
    timeout = parse_timeout(credentials.get("request_timeout"))
    return Diffbot(token, timeout=timeout, transport=GuardedTransport(transport))


def api_error_message(exc: BaseException, token: str) -> str:
    """Safe, user-facing text for an SDK/HTTP failure. Never includes the token."""
    if isinstance(exc, DiffbotError):
        return redact(str(exc), token)
    if isinstance(exc, AuthError):
        return INVALID_TOKEN
    if isinstance(exc, RateLimitError):
        wait = f" Retry after {redact(str(exc.retry_after), token)} seconds." if exc.retry_after else " Retry later."
        return f"Diffbot rate limit exceeded.{wait}"
    if isinstance(exc, ExtractionError):
        if exc.error_code in (401, 403):
            return INVALID_TOKEN
        return f"Diffbot could not extract the page ({exc.error_code}): {redact(exc.error, token)[:300]}"
    if isinstance(exc, JobError):
        # JobError carries plain text, so APIError.message is empty; show the body.
        return f"Diffbot crawl job error: {redact(exc.body or 'job failed', token)[:300]}"
    if isinstance(exc, NotFoundError):
        return "Diffbot did not find that resource."
    if isinstance(exc, APIError):
        detail = redact(exc.message or "request failed", token)[:300]
        return f"Diffbot API error {exc.status_code}: {detail}"
    if isinstance(exc, httpx.TimeoutException):
        return "The Diffbot request timed out."
    if isinstance(exc, (httpx.HTTPError, SdkError)):
        return "The Diffbot request failed before a response was received."
    return "The Diffbot request failed."


@contextmanager
def mapped_errors(client: Diffbot) -> Iterator[None]:
    """Translate SDK/httpx errors to plugin-safe ``DiffbotError`` messages."""
    try:
        yield
    except DiffbotError:
        raise
    except ValidationError as exc:
        raise DiffbotError(redact(str(exc), client.token)) from None
    except json.JSONDecodeError:
        raise DiffbotError("Diffbot returned a non-JSON response.") from None
    except (SdkError, httpx.HTTPError) as exc:
        raise DiffbotError(api_error_message(exc, client.token)) from None


# ---------------------------------------------------------------- credential check


def verify_token(client: Diffbot) -> bool:
    """True if the token is accepted. Never returns the account payload (it holds the token).

    Only an auth failure means False; other errors propagate.
    """
    native = getattr(client, "verify_token", None)
    if callable(native):
        return bool(native())
    try:
        client.request("GET", f"{client.api_base}/v4/account", params={"token": client.token, "days": 1})
    except AuthError:
        return False
    return True


# ---------------------------------------------------------------- extract

EXTRACT_OPTION_WIRE = {
    "timeout": "timeout",
    "mode": "mode",
    "fields": "fields",
    "fallback": "fallback",
    "discussion": "discussion",
    "paging": "paging",
    "max_pages": "maxPages",
    "natural_language": "naturalLanguage",
    "summary_num_sentences": "summaryNumSentences",
    "max_tags": "maxTags",
    "tag_confidence": "tagConfidence",
    "category_confidence": "categoryConfidence",
    "use_proxy": "useProxy",
}
_LIST_OPTIONS = {"fields", "natural_language"}


def _supports_extract_options(client: Diffbot) -> bool:
    try:
        params = inspect.signature(client.extract).parameters
    except (TypeError, ValueError):
        return False
    return "mode" in params or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())


def _wire_value(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ",".join(str(item) for item in value)
    return value


def extract(client: Diffbot, url: str, api: str, fmt: str, options: Mapping[str, Any]) -> ExtractResponse:
    """Extract ``url``. ``options`` use the SDK 3.3.0 keyword names (unset keys omitted)."""
    options = {key: value for key, value in options.items() if value is not None}
    if not options or _supports_extract_options(client):
        return cast(ExtractResponse, client.extract(url, api, fmt, **options))
    # Fallback for SDKs without extract options: same request the SDK builds.
    params: dict[str, Any] = {"token": client.token, "url": url, "timeout": 30000}
    if fmt == "markdown":
        params["mode"] = "llm"
    for key, value in options.items():
        params[EXTRACT_OPTION_WIRE[key]] = _wire_value(value)
    timeout = params.get("timeout")
    per_call = (float(timeout) / 1000.0 + 10.0) if isinstance(timeout, (int, float)) else None
    response = client.request("GET", f"{client.analyze_url}/{api}", params=params, timeout=per_call)
    data = response.json()
    if isinstance(data, dict) and "errorCode" in data:
        raise ExtractionError(data["errorCode"], data.get("error", ""))
    return cast(ExtractResponse, data)


# ---------------------------------------------------------------- crawl


def crawl_start(client: Diffbot, seeds: str, **kwargs: Any) -> str:
    """Create a crawl job (never watches) and return its name."""
    for event in client.crawl(seeds, watch=False, **kwargs):
        name = (event.details or {}).get("job_name")
        if name:
            return str(name)
    raise DiffbotError("Diffbot did not report a crawl job name.")


def crawl_get_job(client: Diffbot, job_name: str) -> CrawlJob:
    job = client.crawl_get_job(job_name)
    if not job:
        raise DiffbotError("Diffbot did not find that crawl job.")
    return cast(CrawlJob, job)


def _download_text(result: Any) -> Any:
    """Coerce a ``crawl_download`` return value (Response, bytes, str, parsed) to text/objects."""
    if isinstance(result, (list, dict)):
        return result
    if hasattr(result, "text"):
        return result.text
    if isinstance(result, (bytes, bytearray)):
        return bytes(result).decode("utf-8", errors="replace")
    return str(result)


def crawl_download(
    client: Diffbot, job_name: str, *, format: str = "json", type: str | None = None, num: int | None = None
) -> Any:
    """Fetch crawl output as parsed rows/objects (a list, or a dict for JSON objects)."""
    if type == "urls":
        format = "csv"  # the URL report is CSV; the JSON decoder would reject it
    native = getattr(client, "crawl_download", None)
    if callable(native):
        raw = native(job_name, format=format, type=type, num=num)
    else:
        params: dict[str, Any] = {"token": client.token, "name": job_name}
        if format and format != "json":
            params["format"] = format
        if type:
            params["type"] = type
        if num is not None:
            params["num"] = num
        raw = client.request("GET", f"{client.crawler_url}/data", params=params, follow_redirects=True)
    data = _download_text(raw)
    if not isinstance(data, str):
        return data
    if not data.strip():
        return []
    try:
        parsed = json.loads(data)
    except ValueError:
        return list(csv.DictReader(io.StringIO(data)))
    if isinstance(parsed, dict) and parsed.get("errorCode"):
        # Same as diffbot 3.3.0: e.g. an unknown job is HTTP 200 + errorCode.
        raise JobError(job_name, f"Crawl data download failed: {parsed.get('error') or 'unexpected response'}")
    return parsed


def as_dict(value: Any, what: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DiffbotError(f"Diffbot {what} returned an unexpected response.")
    return value


__all__ = [
    "GuardedTransport",
    "make_client",
    "mapped_errors",
    "verify_token",
    "extract",
    "crawl_start",
    "crawl_get_job",
    "crawl_download",
]
