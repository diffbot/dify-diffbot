"""Diffbot page extraction tool."""

import re
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotError, normalize_page_url
from tools.common import make_client, mapped_errors, messages, optional_text
from tools.dql_builder import bounded_number
from tools.sdk import as_dict, extract
from tools.shape import summarize_lines, trim_extract

PAGE_TYPES = {"auto", "article", "product", "discussion", "image", "video", "list", "event", "job"}
CUSTOM_API = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


FIELD_PATTERN = re.compile(r"^[A-Za-z0-9_.*,\-]{1,500}$")
# Value sets from the diffbot 3.4.1 types (ExtractMode, ExtractFallback, UseProxy, NaturalLanguageField).
MODES = {"article", "product", "discussion", "image", "video", "list", "event", "llm"}
FALLBACKS = {"article", "product", "discussion", "image", "video", "list", "event"}
PROXIES = {"default", "none"}
NATURAL_LANGUAGE = {
    "entities", "sentiment", "summary", "facts", "openFacts", "records", "categories", "sentences", "language",
}
_NUMBERS = (
    # name, minimum, maximum, integer
    ("max_pages", 1, 100, True),
    ("summary_num_sentences", 1, 20, True),
    ("max_tags", 1, 100, True),
    ("tag_confidence", 0, 1, False),
    ("category_confidence", 0, 1, False),
)
_BOOLEANS = ("discussion", "paging")


def _extract_options(parameters: dict[str, Any]) -> dict[str, Any]:
    """Caller-set Extract options, named as in diffbot 3.4.1; unset ones are omitted."""
    options: dict[str, Any] = {}
    fields = optional_text(parameters, "fields").replace(" ", "")
    if fields:
        if not FIELD_PATTERN.fullmatch(fields):
            raise DiffbotError("fields must be a comma-separated list of field names.")
        options["fields"] = [part for part in fields.split(",") if part]
    for name, allowed in (("mode", MODES), ("fallback", FALLBACKS), ("use_proxy", PROXIES)):
        value = optional_text(parameters, name)
        if value:
            if value not in allowed:
                raise DiffbotError(f"{name} must be one of: {', '.join(sorted(allowed))}.")
            options[name] = value
    timeout = parameters.get("timeout")
    if timeout not in (None, ""):
        # Milliseconds, the Extract API's unit. The plugin runtime kills calls at 300 s.
        options["timeout"] = int(
            bounded_number(timeout, label="timeout", minimum=1000, maximum=250000, integer=True)
        )
    for name, low, high, integer in _NUMBERS:
        value = parameters.get(name)
        if value not in (None, ""):
            number = bounded_number(value, label=name, minimum=low, maximum=high, integer=integer)
            options[name] = int(number) if integer else float(number)
    for name in _BOOLEANS:
        if parameters.get(name) is True:
            options[name] = True  # false is the API default, so only send true
    natural = [part for part in optional_text(parameters, "natural_language").replace(" ", "").split(",") if part]
    if natural:
        bad = [part for part in natural if part not in NATURAL_LANGUAGE]
        if bad:
            raise DiffbotError(f"natural_language must use: {', '.join(sorted(NATURAL_LANGUAGE))}.")
        options["natural_language"] = natural
    return options


class ExtractTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        url = normalize_page_url(optional_text(tool_parameters, "url"))
        page_type = optional_text(tool_parameters, "page_type").lower() or "auto"
        if page_type not in PAGE_TYPES:
            raise DiffbotError(
                "page_type must be auto, article, product, discussion, image, video, list, event, or job."
            )
        # An already-created custom API is called by name; managing custom APIs is out of scope.
        custom_api = optional_text(tool_parameters, "custom_api")
        if custom_api and not CUSTOM_API.fullmatch(custom_api):
            raise DiffbotError("custom_api may use letters, digits, '-' and '_' (100 characters maximum).")
        output_format = optional_text(tool_parameters, "format").lower() or "markdown"
        if output_format not in {"markdown", "json"}:
            raise DiffbotError("format must be markdown or json.")

        options = _extract_options(tool_parameters)
        client = make_client(self.runtime.credentials)
        with client, mapped_errors(client):
            data = as_dict(
                extract(
                    client, url, custom_api or ("analyze" if page_type == "auto" else page_type), output_format, options
                ),
                "extract",
            )
        payload = trim_extract(data)
        payload["url"] = url
        payload["page_type"] = page_type
        if custom_api:
            payload["custom_api"] = custom_api
        lines = []
        for obj in payload["objects"]:
            title = obj.get("title") or obj.get("pageUrl") or "Extracted page"
            kind = obj.get("type") or page_type
            lines.append(f"{title} ({kind})")
            if obj.get("pageUrl"):
                lines.append(obj["pageUrl"])
            if obj.get("text"):
                lines.append(obj["text"][:800])
        if not lines and payload.get("raw_preview"):
            lines.append(payload["raw_preview"][:800])
        summary = summarize_lines(f"Diffbot extract for {url}", lines)
        yield from messages(self, summary, payload)
