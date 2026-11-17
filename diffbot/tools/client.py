"""Plugin policy shared by every tool: token format, URL/host guard, safe errors.

HTTP itself is done by the Diffbot Python SDK (see ``tools/sdk.py``); this module
holds only the rules the plugin enforces on top of it.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9._~+\-]{16,256}$")
BLOCKED_HOST_SUFFIXES = (".local", ".localhost", ".internal")
BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata.google",
}


class DiffbotError(Exception):
    """A safe, user-facing Diffbot failure. Messages never include the token."""


def redact(text: str, token: str | None) -> str:
    """Remove the token (and any ``token=`` query value) from text."""
    if token:
        text = text.replace(token, "[redacted]")
    return re.sub(r"(token=)[^&\s\"']+", r"\1[redacted]", text)


def normalize_token(raw: str) -> str:
    if not isinstance(raw, str):
        raise DiffbotError("Diffbot token is required.")
    cleaned = raw.strip()
    if not cleaned:
        raise DiffbotError("Diffbot token is required.")
    if not TOKEN_PATTERN.fullmatch(cleaned):
        raise DiffbotError(
            "Diffbot token format is invalid. Paste the token from app.diffbot.com without spaces."
        )
    return cleaned


def validate_public_http_url(url: str) -> str:
    """Allow only http(s) URLs whose host is not an obvious local or metadata target.

    Diffbot fetches the page. This check stops the plugin from asking Diffbot to
    call loopback, link-local, or private literal addresses.
    """
    if not isinstance(url, str):
        raise DiffbotError("A page URL is required.")
    url = url.strip()
    if not url:
        raise DiffbotError("A page URL is required.")
    if len(url) > 2048:
        raise DiffbotError("URL is too long.")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise DiffbotError("URL must start with http:// or https://.")
    if parsed.username or parsed.password:
        raise DiffbotError("URL must not include a username or password.")
    check_public_host(parsed.hostname or "")
    return url


def check_public_host(hostname: str) -> None:
    """Reject empty, local-named, metadata, and private/loopback literal hosts."""
    host = hostname.rstrip(".").lower()
    if not host:
        raise DiffbotError("URL must include a host.")
    if host in BLOCKED_HOSTS or host.endswith(BLOCKED_HOST_SUFFIXES):
        raise DiffbotError("URL host is not allowed.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        raise DiffbotError("URL host is not allowed.")


def normalize_page_url(url: str) -> str:
    """Prepend https:// to a bare domain (as the SDK does), then run the host guard."""
    if not isinstance(url, str):
        raise DiffbotError("A page URL is required.")
    url = url.strip()
    if url and "://" not in url:
        url = f"https://{url}"
    return validate_public_http_url(url)
