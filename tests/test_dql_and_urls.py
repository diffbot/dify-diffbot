"""Query building and URL checks. These do not touch the network."""

import pytest

from tools.client import DiffbotError, normalize_token, validate_public_http_url
from tools.dql_builder import build_news_query, build_organizations_query, build_people_query, quote


def test_quote_escapes_breakout_characters():
    quoted = quote('Acme" OR type:Person \\')
    assert quoted == '"Acme\\" OR type:Person \\\\"'
    query = build_organizations_query({"name": 'Acme" OR type:Person'})
    assert query == 'type:Organization name:"Acme\\" OR type:Person"'
    assert " OR type:Person" not in query.replace('\\" OR type:Person', "")


def test_organization_query_requires_a_filter():
    with pytest.raises(DiffbotError, match="at least one filter"):
        build_organizations_query({})


def test_organization_query_includes_numeric_filters():
    query = build_organizations_query(
        {
            "name": "Diffbot",
            "homepage": "https://www.diffbot.com",
            "industry": "Software Companies",
            "city": "Menlo Park",
            "country": "United States",
            "min_employees": 10,
            "max_employees": "500",
            "min_revenue": 1000000,
            "is_public": "false",
        }
    )
    assert query.startswith("type:Organization ")
    assert 'name:"Diffbot"' in query
    assert 'homepageUri:"https://www.diffbot.com"' in query
    assert 'categories.name:"Software Companies"' in query
    assert "nbEmployees>=10" in query
    assert "nbEmployees<=500" in query
    assert "revenue.value>=1000000" in query
    assert "isPublic:false" in query


def test_people_query_uses_employment_fields():
    query = build_people_query({"name": "Ada Lovelace", "employer": "Analytical Engines", "title": "Engineer"})
    assert query.startswith("type:Person ")
    assert 'employments.employer.name:"Analytical Engines"' in query
    assert 'employments.title:"Engineer"' in query


def test_news_query_sorts_descending_and_or_combines_mentions():
    query = build_news_query(
        {
            "mentions": "Diffbot, OpenAI",
            "publisher": "Reuters",
            "language": "EN",
            "since": "2024-01-01",
            "until": "2024-06-30",
        }
    )
    assert "tags.label:or(" in query
    assert '"Diffbot"' in query and '"OpenAI"' in query
    assert 'language:"en"' in query
    assert 'date>="2024-01-01"' in query
    assert query.endswith(" sortBy:date")
    assert "revSortBy" not in query


def test_news_rejects_language_only():
    with pytest.raises(DiffbotError, match="too broad"):
        build_news_query({"language": "en"})


def test_news_rejects_impossible_date():
    with pytest.raises(DiffbotError, match="calendar"):
        build_news_query({"title": "earnings", "since": "2024-02-31"})


def test_token_normalization():
    assert normalize_token("  abcdefghijklmnop  ") == "abcdefghijklmnop"
    with pytest.raises(DiffbotError):
        normalize_token("short")
    with pytest.raises(DiffbotError):
        normalize_token("has whitespace token")
    with pytest.raises(DiffbotError):
        normalize_token("token&other=value1234")


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "https://localhost/secret",
        "https://10.1.2.3/internal",
        "http://169.254.169.254/latest/meta-data",
        "file:///etc/passwd",
        "https://user:pass@example.com/page",
        "https://printer.local/status",
        "javascript:alert(1)",
    ],
)
def test_extract_url_rejects_non_public_targets(url):
    with pytest.raises(DiffbotError):
        validate_public_http_url(url)


def test_extract_url_accepts_public_https():
    assert validate_public_http_url(" https://example.com/a/b ") == "https://example.com/a/b"
