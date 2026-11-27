"""Resolve a free-text industry to a Knowledge Graph ``OrganizationCategory`` name."""

from __future__ import annotations

import difflib
from typing import Any

from tools.client import DiffbotError
from tools.ontology_cache import load_ontology

TAXONOMY = "OrganizationCategory"


def resolve_industry(credentials: dict[str, Any] | None, industry: str) -> str:
    """Exact match first, then case-insensitive; otherwise fail with close suggestions.

    If the ontology cannot be fetched the text is passed through unchanged, so a
    temporary outage does not block searches that would otherwise work.
    """
    try:
        values = load_ontology(credentials).taxonomy_values(TAXONOMY)
    except (DiffbotError, KeyError):
        return industry
    if industry in values:
        return industry
    lowered = {value.lower(): value for value in values}
    if industry.lower() in lowered:
        return lowered[industry.lower()]
    needle = industry.lower()
    contains = [value for value in values if needle in value.lower()]
    close = difflib.get_close_matches(industry, values, n=5, cutoff=0.5)
    suggestions = list(dict.fromkeys(contains[:5] + close))[:5]
    hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else ""
    raise DiffbotError(
        f'"{industry}" is not a Knowledge Graph industry category.{hint} '
        "Use the Knowledge Graph ontology tool (taxonomy_values, OrganizationCategory) to list valid names."
    )
