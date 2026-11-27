"""Start a Diffbot crawl job. Returns the job name, never results."""

import re
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotError, validate_public_http_url
from tools.common import make_client, mapped_errors, messages, optional_text
from tools.dql_builder import bounded_number
from tools.sdk import crawl_start

MAX_JOB_NAME = 30
MAX_PATTERN = 1000
MAX_HEADERS = 10
MAX_HEADER = 500
_EMAIL = re.compile(r"^[^@\s,;<>]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9.\-]{0,251}[A-Za-z0-9])?\.[A-Za-z]{2,63}$")
# Tri-state flags: "default" omits the parameter so the API default applies; off sends 0.
# (Saved Dify forms keep old boolean values, so these fields have new names.)
TRI_STATE = {"default": None, "on": True, "off": False}


def _tri_state(parameters: dict[str, Any], name: str) -> bool | None:
    value = optional_text(parameters, name).lower() or "default"
    if value not in TRI_STATE:
        raise DiffbotError(f"{name} must be default, on, or off.")
    return TRI_STATE[value]


def _headers(raw: str) -> list[str]:
    headers = [line.strip() for line in raw.splitlines() if line.strip()]
    if len(headers) > MAX_HEADERS:
        raise DiffbotError(f"Too many custom headers ({MAX_HEADERS} maximum).")
    if any(len(header) > MAX_HEADER for header in headers):
        raise DiffbotError(f"A custom header is too long ({MAX_HEADER} characters maximum).")
    return headers


def _int(parameters: dict[str, Any], name: str, *, minimum: int, maximum: int) -> int | None:
    value = parameters.get(name)
    if value in (None, ""):
        return None
    return int(bounded_number(value, label=name, minimum=minimum, maximum=maximum, integer=True))


def _seeds(raw: str) -> str:
    parts = raw.split()
    if not parts:
        raise DiffbotError("At least one seed URL is required.")
    if len(parts) > 20:
        raise DiffbotError("Too many seed URLs (20 maximum).")
    checked = []
    for part in parts:
        checked.append(validate_public_http_url(part if "://" in part else f"https://{part}"))
    return " ".join(checked)


class CrawlStartTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        seeds = _seeds(optional_text(tool_parameters, "seeds"))
        kwargs: dict[str, Any] = {}
        name = optional_text(tool_parameters, "job_name")
        if name:
            # The crawler rejects names over 30 characters with HTTP 200 + errorCode 505
            # and creates nothing; the SDK raises APIError for it, but check here for a clearer message.
            if not all(c.isalnum() or c in "-_." for c in name) or len(name) > MAX_JOB_NAME:
                raise DiffbotError(
                    f"job_name may use letters, digits, '-', '_' and '.' ({MAX_JOB_NAME} characters maximum)."
                )
            kwargs["job_name"] = name
        for param, key, low, high in (
            ("max_to_crawl", "max_to_crawl", 1, 10000),
            ("max_to_process", "max_to_process", 1, 10000),
            ("hops", "hops", 0, 10),
        ):
            value = _int(tool_parameters, param, minimum=low, maximum=high)
            if value is not None:
                kwargs[key] = value
        if isinstance(tool_parameters.get("restrict_domain"), bool):
            kwargs["restrict_domain"] = tool_parameters["restrict_domain"]
        for param, key in (
            ("obey_robots_mode", "obey_robots"),
            ("use_proxies_mode", "use_proxies"),
            ("use_canonical_mode", "use_canonical"),
        ):
            flag = _tri_state(tool_parameters, param)
            if flag is not None:
                kwargs[key] = flag
        for param in ("max_to_crawl_per_subdomain", "max_to_process_per_subdomain"):
            value = _int(tool_parameters, param, minimum=1, maximum=10000)
            if value is not None:
                kwargs[param] = value
        delay = tool_parameters.get("crawl_delay")
        if delay not in (None, ""):
            kwargs["crawl_delay"] = float(bounded_number(delay, label="crawl_delay", minimum=-1, maximum=3600))
        for param in ("url_crawl_pattern", "url_process_pattern", "url_crawl_regex", "url_process_regex", "page_process_pattern"):
            value = optional_text(tool_parameters, param)
            if len(value) > MAX_PATTERN:
                raise DiffbotError(f"{param} is too long ({MAX_PATTERN} characters maximum).")
            if value:
                kwargs[param] = value
        headers = _headers(optional_text(tool_parameters, "custom_headers"))
        if headers:
            kwargs["custom_headers"] = headers
        webhook = optional_text(tool_parameters, "notify_webhook")
        if webhook:
            kwargs["notify_webhook"] = validate_public_http_url(webhook)
        email = optional_text(tool_parameters, "notify_email")
        if email:
            if len(email) > 254 or not _EMAIL.fullmatch(email):
                raise DiffbotError("notify_email must be a valid email address.")
            kwargs["notify_email"] = email
        api_url = optional_text(tool_parameters, "api_url")
        if api_url:
            kwargs["api_url"] = validate_public_http_url(api_url)

        client = make_client(self.runtime.credentials)
        with client, mapped_errors(client):
            # watch=False always: polling would outlive the plugin's 300 s call limit.
            job_name = crawl_start(client, seeds, **kwargs)
        payload = {
            "job_name": job_name,
            "seeds": seeds.split(),
            "next": "Use Crawl jobs with action status, then results, with this job_name.",
        }
        yield from messages(
            self,
            f"Started Diffbot crawl job {job_name}. It runs in the background; check it with the Crawl jobs tool.",
            payload,
        )
