"""Look up Knowledge Graph entity types, fields, enums, and taxonomy values."""

import re
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotError
from tools.common import make_client, mapped_errors, messages, optional_text
from tools.ontology_cache import load_ontology
from tools.shape import summarize_lines

LOOKUPS = {
    "types", "composites", "enums", "taxonomies",
    "fields", "taxonomy_values", "enum_values", "find", "raw_file",
}
MAX_SEARCH = 200
MAX_NAME = 100
MAX_ITEMS = 500
_NAME = re.compile(r"^[A-Za-z0-9_.\- ]{1,100}$")


def _literal(search: str) -> str | None:
    """The caller's search as a literal (escaped) pattern, so it cannot be a regex bomb."""
    if not search:
        return None
    if len(search) > MAX_SEARCH:
        raise DiffbotError(f"search is too long ({MAX_SEARCH} characters maximum).")
    return re.escape(search)


def _capped(items: list[Any]) -> tuple[list[Any], bool]:
    return items[:MAX_ITEMS], len(items) > MAX_ITEMS


class KgOntologyTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        lookup = optional_text(tool_parameters, "lookup").lower() or "types"
        if lookup not in LOOKUPS:
            raise DiffbotError(f"lookup must be one of: {', '.join(sorted(LOOKUPS))}.")
        name = optional_text(tool_parameters, "name")
        if name and not _NAME.fullmatch(name):
            raise DiffbotError("name may use letters, digits, '_', '.', '-' and spaces (100 characters maximum).")
        search = _literal(optional_text(tool_parameters, "search"))
        include_deprecated = tool_parameters.get("include_deprecated") is True

        if lookup == "raw_file":
            client = make_client(self.runtime.credentials)
            with client, mapped_errors(client):
                text = client.dql_fetch_ontology_text()
            blob = text.encode("utf-8")
            yield self.create_blob_message(blob, meta={"mime_type": "application/json", "filename": "diffbot-ontology.json"})
            yield from messages(self, f"Diffbot ontology document ({len(blob)} bytes) attached.", {"bytes": len(blob)})
            return

        ontology = load_ontology(self.runtime.credentials)
        payload: dict[str, Any] = {"lookup": lookup}
        lines: list[str] = []
        try:
            if lookup in ("types", "composites", "enums", "taxonomies"):
                names = getattr(ontology, lookup)()
                if search:
                    pattern = re.compile(search, re.IGNORECASE)
                    names = [n for n in names if pattern.search(n)]
                names, truncated = _capped(names)
                payload.update(names=names, truncated=truncated)
                lines = [f"- {n}" for n in names]
            elif lookup == "fields":
                if not name:
                    raise DiffbotError("name (an entity type or composite such as Organization) is required for fields.")
                rows = ontology.filter_fields(ontology.fields_for(name), search, include_deprecated)
                rows, truncated = _capped(rows)
                fields = [
                    {"name": field, "description": ontology.format_field(field, meta), "deprecated": bool(meta.get("isDeprecated"))}
                    for field, meta in rows
                ]
                payload.update(name=name, fields=fields, truncated=truncated)
                lines = [f"- {item['description']}" for item in fields]
            elif lookup == "taxonomy_values":
                if not name:
                    raise DiffbotError("name (a taxonomy such as OrganizationCategory) is required for taxonomy_values.")
                values, truncated = _capped(ontology.taxonomy_values(name, search))
                payload.update(name=name, values=values, truncated=truncated)
                lines = [f"- {v}" for v in values]
            elif lookup == "enum_values":
                if not name:
                    raise DiffbotError("name (an enum such as Language) is required for enum_values.")
                values, truncated = _capped(ontology.enum_values(name))
                payload.update(name=name, values=values, truncated=truncated)
                lines = [f"- {v}" for v in values]
            else:  # find
                if not search:
                    raise DiffbotError("search is required for find.")
                names, truncated = _capped(ontology.find_named(search))
                payload.update(names=names, truncated=truncated)
                lines = [f"- {n}" for n in names]
        except KeyError as exc:
            raise DiffbotError(f"Not found in the ontology: {exc.args[0] if exc.args else name}") from None
        yield from messages(self, summarize_lines(f"Ontology lookup {lookup}.", lines), payload)
