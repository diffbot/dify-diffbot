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


def result_size(parameters: dict[str, Any], *, default: int, maximum: int, minimum: int = 1) -> int:
    value = parameters.get("size")
    if value is None or value == "":
        return default
    number = bounded_number(value, label="size", minimum=minimum, maximum=maximum, integer=True)
    return int(number)


def is_count_only(parameters: dict[str, Any]) -> bool:
    return parameters.get("count_only") is True


def result_offset(parameters: dict[str, Any]) -> int:
    value = parameters.get("offset")
    if value is None or value == "":
        return 0
    return int(bounded_number(value, label="offset", minimum=0, maximum=100000, integer=True))


def fetch_dql(
    credentials: dict[str, Any] | None,
    query: str,
    *,
    size: int,
    offset: int,
    format: str = "json",
    **options: Any,
) -> Any:
    """Run a DQL query through the SDK (POST). ``options`` are the SDK's named DQL options
    (``type``, ``col``, ``filter``, ``filter_exclude``, ``exportspec``, ...); ``None`` is unset.

    The result depends on ``format``: json -> dict, jsonl -> materialized list of entities,
    csv -> str, xls/xlsx -> bytes. Materializing happens inside the guarded client.
    """
    client = make_client(credentials)
    with client, mapped_errors(client):
        result = client.dql(query, size=size, from_=offset, format=format, **options)  # type: ignore[call-overload]
        if format == "jsonl":
            result = list(result)
    return result


def run_dql(credentials: dict[str, Any] | None, query: str, *, size: int, offset: int, **options: Any) -> dict[str, Any]:
    """Run a JSON DQL query through the SDK and record the query that ran."""
    data = as_dict(
        fetch_dql(credentials, query, size=size, offset=offset, **options),
        "Knowledge Graph search",
    )
    data["dql"] = query
    return data


def count_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Result shape for ``count_only``: the query and its hit count, no rows."""
    return {"dql": data.get("dql"), "hits": data.get("hits")}


def messages(tool: Any, summary: str, payload: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
    yield tool.create_text_message(clip(summary))
    yield tool.create_json_message(payload)
