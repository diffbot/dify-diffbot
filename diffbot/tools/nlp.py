"""Diffbot Natural Language analysis of one document."""

import re
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotError
from tools.common import as_dict, make_client, mapped_errors, messages, optional_text
from tools.dql_builder import bounded_number, validate_language
from tools.shape import fit_rows, scrub_private, summarize_lines, trim_resolved_entities

MAX_TEXT = 20000
FIELDS = ("entities", "sentiment", "facts", "records", "categories", "sentences", "language", "summary")
DEFAULT_FIELDS = ("entities", "sentiment")
FORMATS = {"plain text", "plain text with title"}
LIST_FIELDS = ("facts", "records", "categories", "sentences")
LIST_LIMIT = 50
OUTPUT_LIMIT = 100_000
_DOCUMENT_TYPE = re.compile(r"^[A-Za-z0-9 _\-]{1,50}$")


class NlpTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        text = optional_text(tool_parameters, "text")
        if not text:
            raise DiffbotError("Text to analyze is required.")
        if len(text) > MAX_TEXT:
            raise DiffbotError(f"Text is too long ({MAX_TEXT} characters maximum).")
        raw_fields = optional_text(tool_parameters, "fields").replace(" ", "")
        fields = [part for part in raw_fields.split(",") if part] or list(DEFAULT_FIELDS)
        bad = [part for part in fields if part not in FIELDS]
        if bad:
            raise DiffbotError(f"fields must use: {', '.join(FIELDS)}.")
        lang = optional_text(tool_parameters, "lang").lower() or "auto"
        if lang != "auto":
            lang = validate_language(lang)
        fmt = optional_text(tool_parameters, "format").lower() or "plain text"
        if fmt not in FORMATS:
            raise DiffbotError("format must be 'plain text' or 'plain text with title'.")
        document_type = optional_text(tool_parameters, "document_type") or None
        if document_type and not _DOCUMENT_TYPE.fullmatch(document_type):
            raise DiffbotError("document_type may use letters, digits, spaces, '_' and '-' (50 characters maximum).")
        options: dict[str, Any] = {}
        sentences = tool_parameters.get("max_number_of_sentences")
        if sentences not in (None, ""):
            count = int(bounded_number(sentences, label="max_number_of_sentences", minimum=1, maximum=50, integer=True))
            options["custom_summary"] = {"max_number_of_sentences": count}

        client = make_client(self.runtime.credentials)
        with client, mapped_errors(client):
            data = as_dict(
                client.nlp(text, fields=fields, lang=lang, format=fmt, document_type=document_type, **options),  # type: ignore[arg-type]
                "NLP analysis",
            )
        data = scrub_private(data)
        payload: dict[str, Any] = {"fields": fields}
        truncated = False
        if "entities" in data:
            resolved = trim_resolved_entities(data)
            payload["entities"] = resolved["entities"]
            payload["dql_filter"] = resolved["dql_filter"]
        for key in ("sentiment", "language", "summary"):
            if key in data:
                payload[key] = data[key]
        for key in LIST_FIELDS:
            value = data.get(key)
            if isinstance(value, list):
                rows, cut = fit_rows(value[:LIST_LIMIT], OUTPUT_LIMIT // 4)
                payload[key] = rows
                truncated = truncated or cut or len(value) > LIST_LIMIT
            elif key in data:
                payload[key] = value
        payload["truncated"] = truncated
        lines = [f"- {name}: {len(payload[name])}" for name in LIST_FIELDS if isinstance(payload.get(name), list)]
        if payload.get("entities") is not None:
            lines.append(f"- entities: {len(payload['entities'])}")
        if "sentiment" in payload:
            lines.append(f"- sentiment: {payload['sentiment']}")
        yield from messages(self, summarize_lines("Diffbot NLP analysis.", lines), payload)
