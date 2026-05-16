"""Internal LLM gateway client: streaming chat completions + tool-use loop."""

import json
import uuid
from datetime import datetime, timezone
from typing import Callable

import requests
import urllib3

from . import tools as tool_module

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class GatewayClient:
    def __init__(self, cfg: dict) -> None:
        self._url           = cfg["gateway_url"]
        self._api_token     = cfg["api_token"]
        self._cmdb_id       = cfg["cmdb_id"]
        self._cost_center   = cfg.get("cost_center",   "")
        self._business_unit = cfg.get("business_unit", "")
        self._acc_group     = cfg.get("acc_group",     "")
        self._user_id       = cfg.get("user_id",       "")
        self._model         = cfg.get("model",         "gpt-4o")
        self._provider      = cfg.get("provider",      "azure-openai")
        self._max_tokens    = cfg.get("max_tokens",    4096)
        self._temperature   = cfg.get("temperature",   0)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run_turn(
        self,
        messages: list[dict],
        system_prompt: str,
        on_text: Callable[[str], None] | None = None,
    ) -> list[dict]:
        """
        Send messages, handle the tool-use loop, return updated messages list.
        """
        from rich.console import Console
        _console = Console()

        working = list(messages)

        while True:
            full_text, tool_calls, stop_reason = self._stream_once(
                working, system_prompt, on_text
            )

            if tool_calls:
                assistant_msg: dict = {
                    "role": "assistant",
                    "content": full_text or None,
                    "tool_calls": [
                        {
                            "id":   tc["id"],
                            "type": "function",
                            "function": {
                                "name":      tc["name"],
                                "arguments": tc["arguments"],
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            else:
                assistant_msg = {"role": "assistant", "content": full_text}

            working.append(assistant_msg)

            if stop_reason != "tool_calls" or not tool_calls:
                break

            # Execute tools and collect results
            for tc in tool_calls:
                name = tc["name"]
                try:
                    inputs = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except json.JSONDecodeError:
                    inputs = {}

                _console.print(
                    f"\n[bold blue][tool][/bold blue] [cyan]{name}[/cyan]"
                    + (f"({_fmt_inputs(inputs)})" if inputs else "()")
                )
                result_text = tool_module.execute(name, inputs)
                working.append({
                    "role":         "tool",
                    "tool_call_id": tc["id"],
                    "content":      result_text,
                })

        return working

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _stream_once(
        self,
        messages: list[dict],
        system_prompt: str,
        on_text: Callable[[str], None] | None,
    ) -> tuple[str, list[dict], str]:
        all_messages = [{"role": "system", "content": system_prompt}] + messages

        payload = self._build_payload(all_messages)
        headers = {
            "cmdbid":       self._cmdb_id,
            "apitoken":     self._api_token,
            "Content-Type": "application/json",
        }

        response = requests.post(
            self._url,
            json=payload,
            headers=headers,
            verify=False,
            stream=True,
            timeout=120,
        )
        response.raise_for_status()

        full_text   = ""
        stop_reason = "stop"
        tc_acc: dict[int, dict] = {}  # index → {id, name, arguments}

        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            if isinstance(raw_line, bytes):
                raw_line = raw_line.decode("utf-8", errors="replace")
            try:
                outer = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            chunk = outer.get("responsebody") or {}
            if not isinstance(chunk, dict):
                continue
            choices = chunk.get("choices")
            if not choices:
                continue

            choice = choices[0] or {}
            delta  = choice.get("delta") or {}

            text_chunk = delta.get("content") or ""
            if text_chunk:
                full_text += text_chunk
                if on_text:
                    on_text(text_chunk)

            for tc_delta in (delta.get("tool_calls") or []):
                idx = tc_delta.get("index", 0)
                if idx not in tc_acc:
                    tc_acc[idx] = {"id": "", "name": "", "arguments": ""}
                if tc_delta.get("id"):
                    tc_acc[idx]["id"] = tc_delta["id"]
                fn = tc_delta.get("function", {})
                if fn.get("name"):
                    tc_acc[idx]["name"] += fn["name"]
                if fn.get("arguments"):
                    tc_acc[idx]["arguments"] += fn["arguments"]

            fr = choice.get("finish_reason")
            if fr:
                stop_reason = fr
                break

        tool_calls = [tc_acc[i] for i in sorted(tc_acc)]
        return full_text, tool_calls, stop_reason

    def _build_payload(self, messages: list[dict]) -> dict:
        return {
            "requestid":       uuid.uuid4().hex,
            "requestdatetime": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z"),
            "cmdbid":          self._cmdb_id,
            "costcenter":      self._cost_center,
            "businessunit":    self._business_unit,
            "accgroup":        self._acc_group,
            "userid":          self._user_id,
            "provider":        self._provider,
            "apicontext":      "chatcompletions",
            "requestbody": {
                "model":       self._model,
                "messages":    messages,
                "temperature": self._temperature,
                "stream":      True,
                "n":           1,
                "max_tokens":  self._max_tokens,
                "tools":       tool_module.SCHEMAS,
                "tool_choice": "auto",
            },
        }


def _fmt_inputs(inputs: dict) -> str:
    parts = []
    for k, v in inputs.items():
        s = str(v)
        parts.append(f"{k}={s[:60]!r}" if len(s) > 60 else f"{k}={s!r}")
    return ", ".join(parts)
