"""Shared helpers for tool entrypoints."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from tools.sdk import as_dict, make_client, mapped_errors  # noqa: F401  (re-exported for tools)
from tools.dql_builder import bounded_number
from tools.shape import clip


def optional_text(parameters: dict[str, Any], name: str) -> str:
    value = parameters.get(name)
    if value is None:
        return ""
    return str(value).strip()


def result_size(parameters: dict[str, Any], *, default: int, maximum: int) -> int:
    value = parameters.get("size")
    if value is None or value == "":
        return default
    number = bounded_number(value, label="size", minimum=1, maximum=maximum, integer=True)
    return int(number)


def result_offset(parameters: dict[str, Any]) -> int:
    value = parameters.get("offset")
    if value is None or value == "":
        return 0
    return int(bounded_number(value, label="offset", minimum=0, maximum=100000, integer=True))


def run_dql(credentials: dict[str, Any] | None, query: str, *, size: int, offset: int) -> dict[str, Any]:
    """Run a DQL query through the SDK (POST) and record the query that ran."""
    client = make_client(credentials)
    with client, mapped_errors(client):
        data = as_dict(client.dql(query, size=size, from_=offset), "Knowledge Graph search")
    data["dql"] = query
    return data


def messages(tool: Any, summary: str, payload: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
    yield tool.create_text_message(clip(summary))
    yield tool.create_json_message(payload)
