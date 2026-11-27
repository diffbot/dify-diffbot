"""Knowledge Graph organization search."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import count_payload, is_count_only, messages, optional_text, result_offset, result_size, run_dql
from tools.industry import resolve_industry
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
        if parameters["industry"]:
            parameters["industry"] = resolve_industry(self.runtime.credentials, parameters["industry"])
        query = build_organizations_query(parameters)
        count_only = is_count_only(tool_parameters)
        size = 0 if count_only else result_size(tool_parameters, default=5, maximum=100)
        data = run_dql(self.runtime.credentials, query, size=size, offset=result_offset(tool_parameters))
        if count_only:
            payload = count_payload(data)
            yield from messages(self, f"{payload['hits']} matching organization record(s) in the Knowledge Graph.", payload)
            return
        payload = trim_kg(data, "organization", limit=size)
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
