"""Shared helpers for tool entrypoints."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotClient
from tools.dql_builder import bounded_number
from tools.shape import clip


def make_client(credentials: dict[str, Any] | None) -> DiffbotClient:
    raw = ""
    if credentials:
        value = credentials.get("diffbot_token", "")
        raw = value if isinstance(value, str) else ""
    return DiffbotClient(raw)


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


def messages(tool: Any, summary: str, payload: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
    yield tool.create_text_message(clip(summary))
    yield tool.create_json_message(payload)
