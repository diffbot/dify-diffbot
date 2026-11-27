"""Knowledge Graph people search over public professional profiles."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import count_payload, is_count_only, messages, optional_text, result_offset, result_size, run_dql
from tools.dql_builder import build_people_query
from tools.shape import summarize_lines, trim_kg


class SearchPeopleTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        parameters = {
            "name": optional_text(tool_parameters, "name"),
            "employer": optional_text(tool_parameters, "employer"),
            "title": optional_text(tool_parameters, "title"),
            "city": optional_text(tool_parameters, "city"),
            "country": optional_text(tool_parameters, "country"),
        }
        query = build_people_query(parameters)
        count_only = is_count_only(tool_parameters)
        size = 0 if count_only else result_size(tool_parameters, default=5, maximum=100)
        data = run_dql(self.runtime.credentials, query, size=size, offset=result_offset(tool_parameters))
        if count_only:
            payload = count_payload(data)
            yield from messages(self, f"{payload['hits']} matching person record(s) in the Knowledge Graph.", payload)
            return
        payload = trim_kg(data, "person", limit=size)
        lines = []
        for index, row in enumerate(payload["results"], start=1):
            jobs = row.get("employments") or []
            role = ""
            if jobs:
                title = jobs[0].get("title") or ""
                employer = jobs[0].get("employer") or ""
                role = " — " + ", ".join(part for part in (title, employer) if part)
            lines.append(f"{index}. {row.get('name') or 'Unnamed person'}{role}")
        hits = payload.get("hits")
        title = f"People search returned {payload['returned']} public profile(s)"
        if hits is not None:
            title += f" of {hits}"
        title += "."
        yield from messages(self, summarize_lines(title, lines), payload)
