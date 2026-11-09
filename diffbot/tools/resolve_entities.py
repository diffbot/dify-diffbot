"""Named-entity recognition and Knowledge Graph linking."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotError
from tools.common import make_client, messages, optional_text
from tools.dql_builder import validate_language
from tools.shape import summarize_lines, trim_resolved_entities


class ResolveEntitiesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        text = optional_text(tool_parameters, "text")
        if not text:
            raise DiffbotError("Text to analyze is required.")
        if len(text) > 20000:
            raise DiffbotError("Text is too long (20000 characters maximum).")
        lang = optional_text(tool_parameters, "lang").lower() or "auto"
        if lang != "auto":
            lang = validate_language(lang)

        data = make_client(self.runtime.credentials).resolve_entities(text, lang=lang)
        payload = trim_resolved_entities(data)
        lines = []
        for entity in payload["entities"]:
            types = ", ".join(entity.get("types") or [])
            suffix = f" [{types}]" if types else ""
            linked = f" id={entity['id']}" if entity.get("id") else " (not linked)"
            lines.append(f"- {entity.get('name') or 'Unnamed'}{suffix}{linked}")
        if payload.get("dql_filter"):
            lines.append(f"DQL filter: {payload['dql_filter']}")
        summary = summarize_lines(
            f"Resolved {len(payload['entities'])} entities from the supplied text.",
            lines,
        )
        yield from messages(self, summary, payload)
