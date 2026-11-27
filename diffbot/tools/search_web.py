"""Diffbot web search tool."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotError
from tools.common import as_dict, make_client, mapped_errors, messages, optional_text
from tools.dql_builder import bounded_number
from tools.shape import summarize_lines, trim_web_search

SNIPPETS = {"short", "medium", "long", "full"}
QUERY_FIELDS = ("query", "query_2", "query_3", "query_4", "query_5")


def _is_page_lookup(query: str) -> bool:
    parts = query.split()
    return len(parts) == 1 and parts[0].lower().startswith("url:")


class SearchWebTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        # Up to five queries; blanks are dropped before counting.
        queries = [
            text
            for text in (optional_text(tool_parameters, name) for name in QUERY_FIELDS)
            if text
        ]
        if not queries:
            raise DiffbotError("A search query is required.")
        for text in queries:
            if len(text) > 2000:
                raise DiffbotError("Search query is too long (2000 characters maximum each).")
        query = queries[0]

        num_value = tool_parameters.get("num_results")
        if num_value is None or num_value == "":
            num_results = 5
        else:
            num_results = int(
                bounded_number(num_value, label="num_results", minimum=1, maximum=50, integer=True)
            )

        snippet = optional_text(tool_parameters, "snippet_length").lower()
        if not snippet and len(queries) == 1 and _is_page_lookup(query):
            snippet = "full"  # a lone url: query asks for the stored page
        if snippet and snippet not in SNIPPETS:
            raise DiffbotError("snippet_length must be short, medium, long, or full.")

        max_tokens = None
        raw_tokens = tool_parameters.get("max_tokens")
        if raw_tokens not in (None, ""):
            max_tokens = int(
                bounded_number(raw_tokens, label="max_tokens", minimum=500, maximum=32000, integer=True)
            )

        client = make_client(self.runtime.credentials)
        with client, mapped_errors(client):
            # Blank snippet_length is omitted so the API default (long) applies.
            data = as_dict(
                client.web_search(
                    queries[0] if len(queries) == 1 else queries,
                    num_results=num_results,
                    max_tokens=max_tokens,
                    snippet_length=snippet or None,  # type: ignore[arg-type]
                ),
                "web search",
            )
        payload = trim_web_search(data)
        lines = []
        for index, item in enumerate(payload["results"], start=1):
            title = item.get("title") or item.get("pageUrl") or "Untitled"
            score = item.get("score")
            score_text = f" (score {score})" if score is not None else ""
            lines.append(f"{index}. {title}{score_text}")
            if item.get("pageUrl"):
                lines.append(f"   {item['pageUrl']}")
            if item.get("content"):
                lines.append(f"   {item['content'][:400]}")
        summary = summarize_lines(
            f"Diffbot web search returned {len(payload['results'])} result(s).",
            lines,
        )
        yield from messages(self, summary, payload)
