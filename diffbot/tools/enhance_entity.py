"""Enhance a person or organization from partial public identifiers."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotError, validate_public_http_url
from tools.common import make_client, messages, optional_text, result_size
from tools.shape import summarize_lines, trim_enhance


class EnhanceEntityTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        entity_type = optional_text(tool_parameters, "entity_type")
        if entity_type not in {"Organization", "Person"}:
            raise DiffbotError("entity_type must be Organization or Person.")
        name = optional_text(tool_parameters, "name")
        url = optional_text(tool_parameters, "url")
        location = optional_text(tool_parameters, "location")
        employer = optional_text(tool_parameters, "employer")
        title = optional_text(tool_parameters, "title")
        if entity_type == "Organization" and (employer or title):
            raise DiffbotError("employer and title apply only when entity_type is Person.")
        if not any((name, url, employer)):
            raise DiffbotError("Provide a name, a url, or, for a person, an employer.")
        if url:
            url = validate_public_http_url(url)

        params: dict[str, Any] = {
            "type": entity_type,
            "size": result_size(tool_parameters, default=1, maximum=3),
        }
        if name:
            params["name"] = name
        if url:
            params["url"] = url
        if location:
            params["location"] = location
        if employer:
            params["employer"] = employer
        if title:
            params["title"] = title

        data = make_client(self.runtime.credentials).enhance(params)
        payload = trim_enhance(data, entity_type)
        lines = []
        for index, match in enumerate(payload["matches"], start=1):
            entity = match.get("entity") or {}
            score = match.get("score")
            score_text = f" (score {score})" if score is not None else ""
            lines.append(f"{index}. {entity.get('name') or 'Unnamed match'}{score_text}")
            if entity.get("homepageUri"):
                lines.append(f"   {entity['homepageUri']}")
            if entity.get("diffbotUri"):
                lines.append(f"   {entity['diffbotUri']}")
        summary = summarize_lines(
            f"Enhance returned {len(payload['matches'])} {entity_type.lower()} match(es).",
            lines,
        )
        yield from messages(self, summary, payload)
