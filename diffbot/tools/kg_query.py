"""Raw Diffbot Query Language (DQL) search over the Knowledge Graph."""

import re
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotError
from tools.common import count_payload, fetch_dql, is_count_only, messages, optional_text, result_offset, result_size
from tools.shape import fit_rows, scrub_private, summarize_lines

MAX_QUERY = 10_000
MAX_OPTION = 2_000
OUTPUT_LIMIT = 200_000  # characters of JSON returned to the model
EXPORT_LIMIT = 25 * 1024 * 1024  # bytes of a csv/xls/xlsx export file
TYPES = {"query", "text", "queryTextFallback", "crawl"}
JSONMODES = {"extended", "id"}
CLUSTERS = {"all", "best", "dedupe"}
FORMATS = {"json", "jsonl", "csv", "xls", "xlsx"}
FILE_FORMATS = {
    "csv": "text/csv",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
_FILENAME = re.compile(r"^[A-Za-z0-9_\-]{1,80}$")


def _choice(parameters: dict[str, Any], name: str, allowed: set[str]) -> str | None:
    value = optional_text(parameters, name)
    if not value:
        return None
    if value not in allowed:
        raise DiffbotError(f"{name} must be one of: {', '.join(sorted(allowed))}.")
    return value


def _text(parameters: dict[str, Any], name: str, limit: int = MAX_OPTION) -> str | None:
    value = optional_text(parameters, name)
    if not value:
        return None
    if len(value) > limit:
        raise DiffbotError(f"{name} is too long ({limit} characters maximum).")
    return value


def _flag(parameters: dict[str, Any], name: str) -> bool | None:
    return True if parameters.get(name) is True else None  # false is the API default


class KgQueryTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        query = optional_text(tool_parameters, "query")
        if not query:
            raise DiffbotError("A DQL query is required.")
        if len(query) > MAX_QUERY:
            raise DiffbotError(f"The DQL query is too long ({MAX_QUERY} characters maximum).")

        fmt = _choice(tool_parameters, "format", FORMATS) or "json"
        size = result_size(tool_parameters, default=10, maximum=100, minimum=0)
        count_only = is_count_only(tool_parameters) or size == 0
        if count_only:
            size, fmt = 0, "json"  # a count needs no rows or export file

        separator = tool_parameters.get("exportseparator")
        separator = None if separator in (None, "") else str(separator)
        if separator is not None:
            separator = "\t" if separator.lower() in ("tab", "\\t") else separator
            if len(separator) > 5:
                raise DiffbotError("exportseparator is too long.")
        if separator and fmt != "csv":
            raise DiffbotError("exportseparator applies to csv format only.")
        filename = optional_text(tool_parameters, "exportfile")
        if filename and not _FILENAME.fullmatch(filename):
            raise DiffbotError("exportfile may use letters, digits, '-' and '_' (80 characters maximum).")

        options: dict[str, Any] = {
            "type": _choice(tool_parameters, "type", TYPES),
            "col": _text(tool_parameters, "col"),
            "filter": _text(tool_parameters, "filter"),
            "filter_exclude": _text(tool_parameters, "filter_exclude"),
            "exportspec": _text(tool_parameters, "exportspec"),
            "exportseparator": separator,
            "jsonmode": _choice(tool_parameters, "jsonmode", JSONMODES),
            "non_canonical_facts": _flag(tool_parameters, "non_canonical_facts"),
            "no_dedup_articles": _flag(tool_parameters, "no_dedup_articles"),
            "cluster": _choice(tool_parameters, "cluster", CLUSTERS),
        }
        # exportfile is deliberately not sent: a server-side file name means nothing in Dify.
        data = fetch_dql(
            self.runtime.credentials,
            query,
            size=size,
            offset=result_offset(tool_parameters),
            format=fmt,
            **options,
        )

        if fmt in FILE_FORMATS:
            blob = data.encode("utf-8") if isinstance(data, str) else data
            if not isinstance(blob, (bytes, bytearray)):
                raise DiffbotError("Diffbot Knowledge Graph search returned an unexpected response.")
            if len(blob) > EXPORT_LIMIT:
                raise DiffbotError("The export file is too large. Lower size or add a filter.")
            name = f"{filename or 'diffbot-dql'}.{fmt}"
            yield self.create_blob_message(bytes(blob), meta={"mime_type": FILE_FORMATS[fmt], "filename": name})
            note = "Export files are returned as Diffbot sent them and are not scrubbed of contact fields."
            yield from messages(
                self,
                f"DQL {fmt} export attached as {name} ({len(blob)} bytes). {note}",
                {"dql": query, "format": fmt, "filename": name, "bytes": len(blob), "scrubbed": False, "note": note},
            )
            return

        if fmt == "jsonl":
            rows, truncated = fit_rows([scrub_private(row) for row in data], OUTPUT_LIMIT)
            payload: dict[str, Any] = {
                "dql": query, "format": "jsonl", "returned": len(rows), "truncated": truncated, "results": rows,
            }
        else:
            if not isinstance(data, dict):
                raise DiffbotError("Diffbot Knowledge Graph search returned an unexpected response.")
            data = {**data, "dql": query}
            if count_only:
                payload = {**count_payload(data), "count_only": True}
            else:
                payload = scrub_private(data)
                rows, truncated = fit_rows(payload.get("data") or [], OUTPUT_LIMIT)
                if isinstance(payload.get("data"), list):
                    payload["data"] = rows
                payload["returned"] = len(rows)
                payload["truncated"] = truncated
        lines = []
        if payload.get("hits") is not None:
            lines.append(f"hits: {payload['hits']}")
        if payload.get("truncated"):
            lines.append(f"Output was cut at {OUTPUT_LIMIT} characters; lower size or narrow the query.")
        title = "DQL count" if count_only else f"DQL returned {payload.get('returned', 0)} record(s)"
        yield from messages(self, summarize_lines(title + ".", lines), payload)
