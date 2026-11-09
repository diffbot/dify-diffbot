"""Small DQL builder for the v1 Knowledge Graph tools.

Field names are fixed in code. User text is quoted, so a value cannot close
the string and add another clause.
"""

from __future__ import annotations

import datetime as dt
import re

from tools.client import DiffbotError

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LANGUAGE = re.compile(r"^[a-z]{2,3}$")


def quote(value: str, *, label: str = "value") -> str:
    if not isinstance(value, str):
        raise DiffbotError(f"{label} must be text.")
    cleaned = " ".join(value.split())
    if not cleaned:
        raise DiffbotError(f"{label} is empty.")
    if len(cleaned) > 200:
        raise DiffbotError(f"{label} is too long (200 characters maximum).")
    escaped = cleaned.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def clause(field: str, value: str, *, label: str | None = None) -> str:
    return f"{field}:{quote(value, label=label or field)}"


def validate_date(value: str, label: str) -> str:
    if not isinstance(value, str) or not _DATE.fullmatch(value.strip()):
        raise DiffbotError(f"{label} must be a date in YYYY-MM-DD form.")
    try:
        dt.date.fromisoformat(value.strip())
    except ValueError as exc:
        raise DiffbotError(f"{label} is not a real calendar date.") from exc
    return value.strip()


def validate_language(value: str) -> str:
    cleaned = value.strip().lower()
    if not _LANGUAGE.fullmatch(cleaned):
        raise DiffbotError("language must be a 2- or 3-letter ISO code, for example en.")
    return cleaned


def bounded_number(
    value: object,
    *,
    label: str,
    minimum: float,
    maximum: float,
    integer: bool = False,
) -> int | float:
    if isinstance(value, bool) or value is None or value == "":
        raise DiffbotError(f"{label} must be a number.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise DiffbotError(f"{label} must be a number.") from exc
    if number < minimum or number > maximum:
        raise DiffbotError(f"{label} must be between {minimum:g} and {maximum:g}.")
    if integer:
        if not number.is_integer():
            raise DiffbotError(f"{label} must be a whole number.")
        return int(number)
    return int(number) if number.is_integer() else number


def optional_number(
    value: object,
    *,
    label: str,
    minimum: float,
    maximum: float,
    integer: bool = False,
) -> int | float | None:
    if value is None or value == "":
        return None
    return bounded_number(value, label=label, minimum=minimum, maximum=maximum, integer=integer)


def split_terms(value: str, *, label: str, limit: int = 5) -> list[str]:
    parts = [part.strip() for part in value.split(",")]
    terms = [part for part in parts if part]
    if len(terms) > limit:
        raise DiffbotError(f"{label} accepts at most {limit} comma-separated values.")
    return terms


def build_organizations_query(parameters: dict) -> str:
    clauses = ["type:Organization"]
    if parameters.get("name"):
        clauses.append(clause("name", parameters["name"], label="name"))
    if parameters.get("homepage"):
        clauses.append(clause("homepageUri", parameters["homepage"], label="homepage"))
    if parameters.get("industry"):
        clauses.append(clause("categories.name", parameters["industry"], label="industry"))
    if parameters.get("city"):
        clauses.append(clause("location.city.name", parameters["city"], label="city"))
    if parameters.get("country"):
        clauses.append(clause("location.country.name", parameters["country"], label="country"))
    min_employees = optional_number(
        parameters.get("min_employees"), label="min_employees", minimum=0, maximum=10_000_000, integer=True
    )
    max_employees = optional_number(
        parameters.get("max_employees"), label="max_employees", minimum=0, maximum=10_000_000, integer=True
    )
    if min_employees is not None:
        clauses.append(f"nbEmployees>={min_employees}")
    if max_employees is not None:
        clauses.append(f"nbEmployees<={max_employees}")
    min_revenue = optional_number(
        parameters.get("min_revenue"), label="min_revenue", minimum=0, maximum=1e15
    )
    max_revenue = optional_number(
        parameters.get("max_revenue"), label="max_revenue", minimum=0, maximum=1e15
    )
    if min_revenue is not None:
        clauses.append(f"revenue.value>={min_revenue}")
    if max_revenue is not None:
        clauses.append(f"revenue.value<={max_revenue}")
    is_public = parameters.get("is_public") or "any"
    if is_public == "true":
        clauses.append("isPublic:true")
    elif is_public == "false":
        clauses.append("isPublic:false")
    elif is_public != "any":
        raise DiffbotError("is_public must be any, true, or false.")
    if len(clauses) == 1:
        raise DiffbotError(
            "Search organizations needs at least one filter, such as a name, homepage, industry, or location."
        )
    return " ".join(clauses)


def build_people_query(parameters: dict) -> str:
    clauses = ["type:Person"]
    if parameters.get("name"):
        clauses.append(clause("name", parameters["name"], label="name"))
    if parameters.get("employer"):
        clauses.append(clause("employments.employer.name", parameters["employer"], label="employer"))
    if parameters.get("title"):
        clauses.append(clause("employments.title", parameters["title"], label="title"))
    if parameters.get("city"):
        clauses.append(clause("location.city.name", parameters["city"], label="city"))
    if parameters.get("country"):
        clauses.append(clause("location.country.name", parameters["country"], label="country"))
    if len(clauses) == 1:
        raise DiffbotError("Search people needs a name, employer, title, or location.")
    return " ".join(clauses)


def build_news_query(parameters: dict) -> str:
    clauses = ["type:Article"]
    narrowing = False
    if parameters.get("mentions"):
        terms = split_terms(parameters["mentions"], label="mentions")
        if len(terms) == 1:
            clauses.append(clause("tags.label", terms[0], label="mentions"))
        elif terms:
            quoted = ",".join(quote(term, label="mentions") for term in terms)
            clauses.append(f"tags.label:or({quoted})")
        narrowing = bool(terms)
    if parameters.get("text"):
        clauses.append(clause("text", parameters["text"], label="text"))
        narrowing = True
    if parameters.get("title"):
        clauses.append(clause("title", parameters["title"], label="title"))
        narrowing = True
    if parameters.get("publisher"):
        clauses.append(clause("siteName", parameters["publisher"], label="publisher"))
        narrowing = True
    if parameters.get("language"):
        clauses.append(clause("language", validate_language(parameters["language"]), label="language"))
    if parameters.get("since"):
        clauses.append(f'date>={quote(validate_date(parameters["since"], "since"), label="since")}')
        narrowing = True
    if parameters.get("until"):
        clauses.append(f'date<={quote(validate_date(parameters["until"], "until"), label="until")}')
        narrowing = True
    if not narrowing:
        raise DiffbotError(
            "Search news needs a mention, title, text, publisher, or date. An unfiltered article query is too broad."
        )
    # revSortBy is descending. Article publication dates increase with time,
    # so this asks for newest first. diffbot-mcp currently appends sortBy:date
    # while describing the same newest-first intent; confirm with a live token.
    clauses.append("revSortBy:date")
    return " ".join(clauses)
