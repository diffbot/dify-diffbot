"""Process-wide cache of the Knowledge Graph ontology.

The ontology document is public: the SDK fetches it without a token, so it is the same
for every credential and differs only by URL. One parsed ``Ontology`` per resolved URL is
held for 24 hours. A failed refresh serves the stale copy, and after a failed fetch with
nothing to serve the cache backs off for about five minutes instead of refetching on every call.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from diffbot import Diffbot
from diffbot.ontology import Ontology

from tools.client import DiffbotError
from tools.sdk import make_client, mapped_errors

TTL_SECONDS = 24 * 60 * 60
BACKOFF_SECONDS = 5 * 60


@dataclass
class _Entry:
    ontology: Ontology | None = None
    fetched_at: float = 0.0
    retry_after: float = 0.0


class OntologyCache:
    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        ttl: float = TTL_SECONDS,
        backoff: float = BACKOFF_SECONDS,
    ) -> None:
        self._clock = clock
        self._ttl = ttl
        self._backoff = backoff
        self._lock = threading.Lock()
        self._entries: dict[str, _Entry] = {}

    def get(self, client: Diffbot) -> Ontology:
        """Return the ontology for ``client.ontology_url``, fetching at most once per TTL.

        The lock is held across the fetch so concurrent callers share one download.
        """
        url = client.ontology_url
        with self._lock:
            now = self._clock()
            entry = self._entries.setdefault(url, _Entry())
            if entry.ontology is not None and now - entry.fetched_at < self._ttl:
                return entry.ontology
            if now < entry.retry_after:
                if entry.ontology is not None:
                    return entry.ontology
                raise DiffbotError("The Knowledge Graph ontology is temporarily unavailable. Try again in a few minutes.")
            try:
                ontology = client.dql_fetch_ontology()
                if not isinstance(getattr(ontology, "data", None), dict):
                    # e.g. an error page or a JSON list: do not cache something the lookups cannot read
                    raise DiffbotError("Diffbot returned an unexpected ontology document.")
            except Exception:
                entry.retry_after = now + self._backoff
                if entry.ontology is not None:
                    return entry.ontology  # stale beats nothing
                raise
            entry.ontology = ontology
            entry.fetched_at = now
            entry.retry_after = 0.0
            return ontology

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


CACHE = OntologyCache()


def load_ontology(credentials: dict[str, Any] | None, cache: OntologyCache | None = None) -> Ontology:
    """Fetch (or reuse) the ontology through the normal guarded client."""
    client = make_client(credentials)  # a valid-format token is required even though none is sent
    with client, mapped_errors(client):
        return (cache or CACHE).get(client)
