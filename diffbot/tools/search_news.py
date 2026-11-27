"""Knowledge Graph news and article search."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import count_payload, is_count_only, messages, optional_text, result_offset, result_size, run_dql
from tools.dql_builder import build_news_query
from tools.shape import summarize_lines, trim_kg


class SearchNewsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        parameters = {
            "mentions": optional_text(tool_parameters, "mentions"),
            "text": optional_text(tool_parameters, "text"),
            "title": optional_text(tool_parameters, "title"),
            "publisher": optional_text(tool_parameters, "publisher"),
            "language": optional_text(tool_parameters, "language"),
            "since": optional_text(tool_parameters, "since"),
            "until": optional_text(tool_parameters, "until"),
        }
        query = build_news_query(parameters)
        count_only = is_count_only(tool_parameters)
        size = 0 if count_only else result_size(tool_parameters, default=5, maximum=100)
        include_text = bool(tool_parameters.get("include_text"))
        data = run_dql(self.runtime.credentials, query, size=size, offset=result_offset(tool_parameters))
        if count_only:
            payload = count_payload(data)
            yield from messages(self, f"{payload['hits']} matching article record(s) in the Knowledge Graph.", payload)
            return
        payload = trim_kg(data, "article", include_text=include_text, limit=size)
        lines = []
        for index, row in enumerate(payload["results"], start=1):
            headline = row.get("title") or "Untitled article"
            publisher = row.get("siteName") or ""
            when = row.get("date") or ""
            suffix = " — ".join(part for part in (publisher, str(when) if when else "") if part)
            lines.append(f"{index}. {headline}" + (f" ({suffix})" if suffix else ""))
            if row.get("pageUrl"):
                lines.append(f"   {row['pageUrl']}")
        hits = payload.get("hits")
        title = f"News search returned {payload['returned']} article(s)"
        if hits is not None:
            title += f" of {hits}"
        title += ", newest publication date first."
        yield from messages(self, summarize_lines(title, lines), payload)
