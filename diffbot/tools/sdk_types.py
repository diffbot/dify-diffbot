"""Response shapes the plugin reads from the Diffbot SDK.

TODO(diffbot 3.3.0): the SDK ships response TypedDicts in ``diffbot.types``. Until
the pin requires it, these local ``total=False`` equivalents describe only the
fields this plugin touches. Delete the fallback once ``diffbot>=3.3.0`` is pinned.
"""

from __future__ import annotations

from typing import Any, TypedDict

try:  # diffbot >= 3.3.0 ships these; prefer them.
    from diffbot.types import CrawlJob, ExtractResponse  # type: ignore[attr-defined]

    SDK_TYPES = True
except ImportError:  # diffbot 3.2.x: local equivalents below
    SDK_TYPES = False


if not SDK_TYPES:

    class ExtractResponse(TypedDict, total=False):  # type: ignore[no-redef]
        objects: list[dict[str, Any]]
        humanLanguage: str
        errorCode: int
        error: str

    class CrawlJobStatus(TypedDict, total=False):
        status: int
        message: str

    class CrawlJob(TypedDict, total=False):  # type: ignore[no-redef]
        name: str
        jobStatus: CrawlJobStatus
        pageCrawlSuccesses: int
        pageProcessSuccesses: int
        objectsFound: int
