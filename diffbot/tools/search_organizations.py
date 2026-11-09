"""Knowledge Graph organization search."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import make_client, messages, optional_text, result_size
from tools.dql_builder import build_organizations_query
from tools.shape import summarize_lines, trim_kg


class SearchOrganizationsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        parameters = {
            "name": optional_text(tool_parameters, "name"),
            "homepage": optional_text(tool_parameters, "homepage"),
            "industry": optional_text(tool_parameters, "industry"),
            "city": optional_text(tool_parameters, "city"),
            "country": optional_text(tool_parameters, "country"),
            "min_employees": tool_parameters.get("min_employees"),
            "max_employees": tool_parameters.get("max_employees"),
            "min_revenue": tool_parameters.get("min_revenue"),
            "max_revenue": tool_parameters.get("max_revenue"),
            "is_public": optional_text(tool_parameters, "is_public").lower() or "any",
        }
        query = build_organizations_query(parameters)
        size = result_size(tool_parameters, default=5, maximum=10)
        data = make_client(self.runtime.credentials).dql(query, size=size)
        data["dql"] = query
        payload = trim_kg(data, "organization")
        lines = []
        for index, row in enumerate(payload["results"], start=1):
            location = row.get("location") or {}
            where = ", ".join(
                part for part in (location.get("city"), location.get("country")) if part
            )
            extra = f" — {where}" if where else ""
            lines.append(f"{index}. {row.get('name') or 'Unnamed organization'}{extra}")
            if row.get("homepageUri"):
                lines.append(f"   {row['homepageUri']}")
            if row.get("summary"):
                lines.append(f"   {row['summary'][:240]}")
        hits = payload.get("hits")
        title = f"Organization search returned {payload['returned']} record(s)"
        if hits is not None:
            title += f" of {hits}"
        title += "."
        yield from messages(self, summarize_lines(title, lines), payload)
