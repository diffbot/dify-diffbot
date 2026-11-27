"""Diffbot account plan, status, and recent usage. Never returns the token or email."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.common import as_dict, make_client, mapped_errors, messages
from tools.dql_builder import bounded_number
from tools.shape import summarize_lines

DEFAULT_DAYS = 7
USAGE_KEYS = ("date", "nlp", "credits", "extractions", "proxies", "entities", "refresh", "facets", "videos", "subtitles")


def _usage_row(row: Any) -> dict[str, Any]:
    return {key: row[key] for key in USAGE_KEYS if isinstance(row, dict) and key in row}


class AccountUsageTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        raw_days = tool_parameters.get("days")
        days = DEFAULT_DAYS if raw_days in (None, "") else int(
            bounded_number(raw_days, label="days", minimum=1, maximum=366, integer=True)
        )
        client = make_client(self.runtime.credentials)
        with client, mapped_errors(client):
            data = as_dict(client.account(days=days), "account")
        # Allowlist only: the response also holds the token, child tokens and the account email.
        usage = [_usage_row(row) for row in (data.get("usage") or [])[:366]] if isinstance(data.get("usage"), list) else []
        payload = {"plan": data.get("plan"), "status": data.get("status"), "days": days, "usage": usage}
        lines = [f"{row.get('date', '?')}: " + ", ".join(f"{k} {v}" for k, v in row.items() if k != "date") for row in usage[:30]]
        title = f"Diffbot plan {payload['plan'] or 'unknown'} ({payload['status'] or 'unknown'}), last {days} day(s)."
        yield from messages(self, summarize_lines(title, lines), payload)
