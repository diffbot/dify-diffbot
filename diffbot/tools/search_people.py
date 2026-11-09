"""Knowledge Graph people search over public professional profiles."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import make_client, messages, optional_text, result_size
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
        size = result_size(tool_parameters, default=5, maximum=10)
        data = make_client(self.runtime.credentials).dql(query, size=size)
        data["dql"] = query
        payload = trim_kg(data, "person")
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
