"""List, inspect, fetch results of, and delete Diffbot crawl jobs."""

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotError
from tools.common import make_client, mapped_errors, messages, optional_text
from tools.dql_builder import bounded_number
from tools.sdk import crawl_download, crawl_get_job
from tools.shape import clip, summarize_lines

ACTIONS = {"list", "status", "results", "delete"}
RESULT_LIMIT = 1000
JOB_FIELDS = ("name", "jobStatus", "pageCrawlAttempts", "pageCrawlSuccesses", "pageProcessAttempts",
              "pageProcessSuccesses", "objectsFound", "urlsFound", "maxToCrawl", "maxToProcess")


def _job_summary(job: dict[str, Any]) -> dict[str, Any]:
    out = {key: job[key] for key in JOB_FIELDS if key in job}
    status = out.get("jobStatus")
    if isinstance(status, dict):
        out["jobStatus"] = {k: status[k] for k in ("status", "message") if k in status}
    return out


def _cell(value: Any) -> Any:
    return clip(value, 500) if isinstance(value, str) else value


class CrawlJobsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        action = optional_text(tool_parameters, "action").lower()
        if action not in ACTIONS:
            raise DiffbotError("action must be list, status, results, or delete.")
        job_name = optional_text(tool_parameters, "job_name")
        if action != "list" and not job_name:
            raise DiffbotError("job_name is required for this action.")

        client = make_client(self.runtime.credentials)
        with client, mapped_errors(client):
            if action == "list":
                jobs = [_job_summary(job) for job in client.crawl_list_jobs()[:100]]
                lines = [f"- {job.get('name')}: {(job.get('jobStatus') or {}).get('message', '')}" for job in jobs]
                yield from messages(
                    self, summarize_lines(f"{len(jobs)} crawl job(s).", lines), {"jobs": jobs}
                )
            elif action == "status":
                job = _job_summary(dict(crawl_get_job(client, job_name)))
                message = (job.get("jobStatus") or {}).get("message", "")
                yield from messages(self, f"Crawl job {job_name}: {message}".strip(), {"job": job})
            elif action == "results":
                limit = int(
                    bounded_number(
                        tool_parameters.get("limit") or RESULT_LIMIT,
                        label="limit", minimum=1, maximum=RESULT_LIMIT, integer=True,
                    )
                )
                kind = optional_text(tool_parameters, "result_type").lower()
                if kind not in ("", "urls"):
                    raise DiffbotError("result_type must be empty or urls.")
                data = crawl_download(client, job_name, format="json", type=kind or None, num=limit)
                rows = data if isinstance(data, list) else [data]
                kept = [{k: _cell(v) for k, v in row.items()} if isinstance(row, dict) else row for row in rows[:limit]]
                payload = {
                    "job_name": job_name,
                    "returned": len(kept),
                    "truncated": len(rows) > limit,
                    "results": kept,
                }
                yield from messages(
                    self, f"Crawl job {job_name} returned {len(kept)} row(s)"
                    + (" (truncated)." if payload["truncated"] else "."), payload
                )
            else:  # delete
                client.crawl_delete_job(job_name)
                yield from messages(self, f"Deleted crawl job {job_name} and its data.", {"deleted": job_name})
