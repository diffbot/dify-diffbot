"""Diffbot page extraction tool."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotError, validate_public_http_url
from tools.common import make_client, messages, optional_text
from tools.shape import summarize_lines, trim_extract

PAGE_TYPES = {"auto", "article", "product", "discussion", "image", "video", "list", "event"}


class ExtractTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        url = validate_public_http_url(optional_text(tool_parameters, "url"))
        page_type = optional_text(tool_parameters, "page_type").lower() or "auto"
        if page_type not in PAGE_TYPES:
            raise DiffbotError(
                "page_type must be auto, article, product, discussion, image, video, list, or event."
            )
        output_format = optional_text(tool_parameters, "format").lower() or "markdown"
        if output_format not in {"markdown", "json"}:
            raise DiffbotError("format must be markdown or json.")

        data = make_client(self.runtime.credentials).extract(
            url,
            page_type=page_type,
            markdown=(output_format == "markdown"),
        )
        payload = trim_extract(data)
        payload["url"] = url
        payload["page_type"] = page_type
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
