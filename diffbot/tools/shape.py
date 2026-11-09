"""Trim Diffbot payloads before they are returned to a model.

Knowledge Graph records can contain emails, phone numbers, and long HTML.
v1 keeps the fields an agent needs for citation and lookup, and drops the rest
even if the API included them.
"""

from __future__ import annotations

import json
from typing import Any

TEXT_LIMIT = 4000
SUMMARY_LIMIT = 6000


def clip(value: object, limit: int = TEXT_LIMIT) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _place(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    place: dict[str, str] = {}
    for level in ("city", "region", "country"):
        nested = value.get(level)
        name = nested.get("name") if isinstance(nested, dict) else None
        if isinstance(name, str) and name:
            place[level] = name
    return place


def _entity_id(entity: dict[str, Any]) -> str | None:
    raw = entity.get("id") or entity.get("diffbotUri") or ""
    if not isinstance(raw, str) or not raw:
        return None
    return raw.rstrip("/").rsplit("/", 1)[-1] or None


def trim_organization(entity: dict[str, Any]) -> dict[str, Any]:
    categories = []
    for category in entity.get("categories") or []:
        if isinstance(category, dict) and category.get("name"):
            categories.append(
                {"name": category.get("name"), "isPrimary": bool(category.get("isPrimary"))}
            )
        if len(categories) >= 5:
            break
    revenue = entity.get("revenue") if isinstance(entity.get("revenue"), dict) else {}
    record: dict[str, Any] = {
        "name": entity.get("name"),
        "homepageUri": entity.get("homepageUri"),
        "summary": clip(entity.get("summary") or entity.get("descriptors") or "", 500),
        "nbEmployees": entity.get("nbEmployees"),
        "revenue": revenue.get("value") if isinstance(revenue, dict) else None,
        "revenueCurrency": revenue.get("currency") if isinstance(revenue, dict) else None,
        "isPublic": entity.get("isPublic"),
        "location": _place(entity.get("location")),
        "categories": categories,
        "id": _entity_id(entity),
        "diffbotUri": entity.get("diffbotUri"),
    }
    return {key: value for key, value in record.items() if value not in (None, "", [], {})}


def trim_person(entity: dict[str, Any]) -> dict[str, Any]:
    employments = []
    for job in entity.get("employments") or []:
        if not isinstance(job, dict):
            continue
        employer = job.get("employer") if isinstance(job.get("employer"), dict) else {}
        employments.append(
            {
                "title": job.get("title"),
                "employer": employer.get("name"),
                "isCurrent": job.get("isCurrent"),
            }
        )
        if len(employments) >= 3:
            break
    record: dict[str, Any] = {
        "name": entity.get("name"),
        "summary": clip(entity.get("summary") or entity.get("description") or "", 500),
        "employments": employments,
        "location": _place(entity.get("location")),
        "linkedInUri": entity.get("linkedInUri"),
        "id": _entity_id(entity),
        "diffbotUri": entity.get("diffbotUri"),
    }
    return {key: value for key, value in record.items() if value not in (None, "", [], {})}


def trim_article(entity: dict[str, Any], *, include_text: bool) -> dict[str, Any]:
    date = entity.get("date")
    if isinstance(date, dict):
        date = date.get("str") or date.get("timestamp")
    record: dict[str, Any] = {
        "title": entity.get("title"),
        "date": date,
        "siteName": entity.get("siteName"),
        "author": entity.get("author"),
        "language": entity.get("language"),
        "sentiment": entity.get("sentiment"),
        "pageUrl": entity.get("pageUrl") or entity.get("resolvedPageUrl"),
        "summary": clip(entity.get("summary") or "", 800),
        "id": _entity_id(entity),
    }
    if include_text:
        record["text"] = clip(entity.get("text") or "", TEXT_LIMIT)
    return {key: value for key, value in record.items() if value not in (None, "", [], {})}


def trim_kg(data: dict[str, Any], kind: str, *, include_text: bool = False) -> dict[str, Any]:
    rows = []
    for item in (data.get("data") or [])[:20]:
        entity = item.get("entity") if isinstance(item, dict) and "entity" in item else item
        if not isinstance(entity, dict):
            continue
        if kind == "organization":
            rows.append(trim_organization(entity))
        elif kind == "person":
            rows.append(trim_person(entity))
        else:
            rows.append(trim_article(entity, include_text=include_text))
    return {
        "dql": data.get("dql"),
        "hits": data.get("hits"),
        "returned": len(rows),
        "results": rows,
    }


def trim_enhance(data: dict[str, Any], kind: str) -> dict[str, Any]:
    matches = []
    for item in (data.get("data") or [])[:5]:
        if not isinstance(item, dict):
            continue
        entity = item.get("entity") if isinstance(item.get("entity"), dict) else {}
        trimmed = trim_organization(entity) if kind == "Organization" else trim_person(entity)
        matches.append({"score": item.get("score"), "entity": trimmed})
    return {"hits": data.get("hits"), "matches": matches}


def trim_extract(data: dict[str, Any]) -> dict[str, Any]:
    objects = data.get("objects")
    trimmed = []
    if isinstance(objects, list):
        for obj in objects[:5]:
            if not isinstance(obj, dict):
                continue
            text = obj.get("markdown") or obj.get("text") or obj.get("html") or ""
            record = {
                "type": obj.get("type"),
                "title": clip(obj.get("title") or "", 300),
                "author": obj.get("author"),
                "date": obj.get("date"),
                "siteName": obj.get("siteName"),
                "pageUrl": obj.get("pageUrl") or obj.get("resolvedPageUrl") or obj.get("url"),
                "text": clip(text, TEXT_LIMIT),
            }
            trimmed.append({key: value for key, value in record.items() if value not in (None, "")})
    payload: dict[str, Any] = {"objects": trimmed}
    if data.get("humanLanguage"):
        payload["humanLanguage"] = data.get("humanLanguage")
    if not trimmed:
        payload["raw_preview"] = clip(json.dumps(data, default=str), TEXT_LIMIT)
    return payload


def trim_web_search(data: dict[str, Any]) -> dict[str, Any]:
    results = []
    for item in (data.get("search_results") or [])[:20]:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "score": item.get("score"),
                "title": item.get("title"),
                "pageUrl": item.get("pageUrl"),
                "date": item.get("date"),
                "content": clip(item.get("content") or "", TEXT_LIMIT),
            }
        )
    return {
        "query": data.get("query"),
        "timeMs": data.get("timeMs"),
        "results": results,
    }


def trim_resolved_entities(data: dict[str, Any]) -> dict[str, Any]:
    entities = []
    for entity in (data.get("entities") or [])[:25]:
        if not isinstance(entity, dict):
            continue
        types = []
        for type_info in entity.get("allTypes") or []:
            if isinstance(type_info, dict) and type_info.get("name"):
                types.append(type_info["name"])
        uri = entity.get("id") or entity.get("diffbotUri") or ""
        entity_id = uri.rstrip("/").rsplit("/", 1)[-1] if isinstance(uri, str) and uri else None
        entities.append(
            {
                "name": entity.get("name"),
                "types": types,
                "confidence": entity.get("confidence"),
                "salience": entity.get("salience"),
                "sentiment": entity.get("sentiment"),
                "id": entity_id,
                "mentions": len(entity.get("mentions") or []),
            }
        )
    ids = [entity["id"] for entity in entities if entity.get("id")]
    dql_filter = None
    if ids:
        quoted = ",".join(f'"{entity_id}"' for entity_id in ids)
        dql_filter = f"id:or({quoted})"
    return {
        "sentiment": data.get("sentiment"),
        "entities": entities,
        "dql_filter": dql_filter,
    }


def summarize_lines(title: str, lines: list[str]) -> str:
    body = "\n".join(lines) if lines else "No matching records."
    return clip(f"{title}\n{body}", SUMMARY_LIMIT)
