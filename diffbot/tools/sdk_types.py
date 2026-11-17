"""Response shapes the plugin reads from the Diffbot SDK.

TODO(diffbot 3.3.0): the SDK will ship response TypedDicts (``AccountResponse`` and
friends). Until it does these local, ``total=False`` equivalents describe only the
fields this plugin touches. Swap them for ``from diffbot.types import ...`` then.
"""

from __future__ import annotations

from typing import Any, TypedDict

try:  # diffbot >= 3.3.0 ships these; prefer them.
    from diffbot.types import (  # type: ignore[attr-defined]
        CrawlJob,
        CrawlJobStatus,
        DqlResponse,
        EntitiesResponse as NlpResponse,
        ExtractResponse,
        WebSearchResponse,
    )

    SDK_TYPES = True
except ImportError:  # diffbot 3.2.x: local equivalents below
    SDK_TYPES = False


if not SDK_TYPES:
    class ExtractResponse(TypedDict, total=False):
        objects: list[dict[str, Any]]
        humanLanguage: str
        errorCode: int
        error: str


    class WebSearchResponse(TypedDict, total=False):
        query: list[str]
        timeMs: int
        search_results: list[dict[str, Any]]


    class DqlResponse(TypedDict, total=False):
        hits: int
        data: list[dict[str, Any]]
        dql: str


    class NlpResponse(TypedDict, total=False):
        entities: list[dict[str, Any]]
        sentiment: float
        language: str


    class CrawlJobStatus(TypedDict, total=False):
        status: int
        message: str


    class CrawlJob(TypedDict, total=False):
        name: str
        jobStatus: CrawlJobStatus
        pageCrawlSuccesses: int
        pageProcessSuccesses: int
        objectsFound: int
