"""Ask Diffbot's LLM a question; it answers using Diffbot's web and Knowledge Graph search."""

import json
from collections.abc import Generator
from typing import Any

from diffbot import ValidationError
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.client import DiffbotError
from tools.common import make_client, mapped_errors, messages, optional_text
from tools.shape import clip

MAX_QUESTION = 8000
MAX_SYSTEM = 8000
MAX_SCHEMA_BYTES = 20_000
MAX_ANSWER = 60_000  # characters of streamed or joined text
OUTPUTS = {"text", "json", "json_schema"}


def _schema(raw: str) -> dict[str, Any]:
    if len(raw.encode("utf-8")) > MAX_SCHEMA_BYTES:
        raise DiffbotError("json_schema is too large (20 KB maximum).")
    try:
        parsed = json.loads(raw)
    except ValueError:
        raise DiffbotError("json_schema must be valid JSON.") from None
    if not isinstance(parsed, dict):
        raise DiffbotError("json_schema must be a JSON object.")
    return parsed


class AskTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        question = optional_text(tool_parameters, "question")
        if not question:
            raise DiffbotError("A question is required.")
        if len(question) > MAX_QUESTION:
            raise DiffbotError(f"The question is too long ({MAX_QUESTION} characters maximum).")
        system_prompt = optional_text(tool_parameters, "system_prompt")
        if len(system_prompt) > MAX_SYSTEM:
            raise DiffbotError(f"system_prompt is too long ({MAX_SYSTEM} characters maximum).")
        output = optional_text(tool_parameters, "output").lower() or "text"
        if output not in OUTPUTS:
            raise DiffbotError("output must be text, json, or json_schema.")
        schema = None
        if output == "json_schema":
            raw_schema = optional_text(tool_parameters, "json_schema")
            if not raw_schema:
                raise DiffbotError("json_schema is required when output is json_schema.")
            schema = _schema(raw_schema)
        # The stream flag only controls progressive text; json output is always read whole.
        stream = tool_parameters.get("stream") is not False and output == "text"

        chat: list[dict[str, str]] = []
        if system_prompt:
            chat.append({"role": "system", "content": system_prompt})
        chat.append({"role": "user", "content": question})

        client = make_client(self.runtime.credentials)
        if output != "text":
            with client, mapped_errors(client):
                try:
                    # ask_json builds a json_schema response format (never bare json_object).
                    answer: Any = client.ask_json(chat, schema)  # type: ignore[arg-type]
                except ValidationError:
                    raise DiffbotError(
                        "Diffbot did not return valid JSON for that request. Try again or simplify the schema."
                    ) from None
            yield from messages(self, clip(json.dumps(answer, default=str), 4000), {"output": output, "answer": answer})
            return

        parts: list[str] = []
        used = 0
        truncated = False
        # Iterate inside the guard so a 401/429 or a dropped connection mid-stream is mapped.
        with client, mapped_errors(client):
            for chunk in client.ask(chat):
                room = MAX_ANSWER - used
                if room <= 0:
                    truncated = True
                    break
                if len(chunk) > room:
                    chunk, truncated = chunk[:room], True
                used += len(chunk)
                parts.append(chunk)
                if stream:
                    yield self.create_text_message(chunk)
                if truncated:
                    break
        answer_text = "".join(parts)
        if not stream:
            yield self.create_text_message(answer_text or "Diffbot returned an empty answer.")
        yield self.create_json_message({"output": "text", "answer": answer_text, "truncated": truncated})
