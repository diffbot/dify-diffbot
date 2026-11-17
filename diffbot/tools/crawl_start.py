"""Start a Diffbot crawl job. Returns the job name, never results."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotError, validate_public_http_url
from tools.common import make_client, mapped_errors, messages, optional_text
from tools.dql_builder import bounded_number
from tools.sdk import crawl_start


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
            if not all(c.isalnum() or c in "-_." for c in name) or len(name) > 100:
                raise DiffbotError("job_name may use letters, digits, '-', '_' and '.' (100 characters maximum).")
            kwargs["job_name"] = name
        for param, key, low, high in (
            ("max_to_crawl", "max_to_crawl", 1, 10000),
            ("max_to_process", "max_to_process", 1, 10000),
            ("hops", "hops", 0, 10),
        ):
            value = _int(tool_parameters, param, minimum=low, maximum=high)
            if value is not None:
                kwargs[key] = value
        for param in ("restrict_domain", "obey_robots", "use_proxies"):
            if isinstance(tool_parameters.get(param), bool):
                kwargs[param] = tool_parameters[param]
        delay = tool_parameters.get("crawl_delay")
        if delay not in (None, ""):
            kwargs["crawl_delay"] = float(bounded_number(delay, label="crawl_delay", minimum=-1, maximum=3600))
        for param in ("url_crawl_pattern", "url_process_pattern", "custom_headers"):
            value = optional_text(tool_parameters, param)
            if value:
                kwargs[param] = value
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
