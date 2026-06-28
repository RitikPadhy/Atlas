"""Ollama backend — local models via the Ollama HTTP API.

Owns the Ollama-specific quirks: the request shape, the GPU keep_alive, and
normalizing however the model emitted its tool calls (native `tool_calls`,
`<tool_call>` tags, or a bare JSON object in the text) into the canonical form.
"""
import json
import re

import ollama_client
from .base import Backend, BackendError

_TOOL_TAG = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def _norm_call(obj):
    if not isinstance(obj, dict):
        return None
    if "function" in obj and isinstance(obj["function"], dict):
        fn = obj["function"]
        name, args = fn.get("name"), fn.get("arguments", {})
    else:
        name = obj.get("name")
        args = obj.get("arguments", obj.get("parameters", {}))
    if not name:
        return None
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = {}
    return {"name": name, "arguments": args or {}}


def normalize(msg):
    """(tool_calls, answer_text) from an Ollama assistant message dict."""
    native = msg.get("tool_calls")
    if native:
        calls = [c for c in (_norm_call(c) for c in native) if c]
        if calls:
            return calls, ""

    content = _THINK.sub("", msg.get("content") or "").strip()
    if not content:
        return [], ""

    blobs = [m.group(1) for m in _TOOL_TAG.finditer(content)]
    blobs += [m.group(1) for m in _FENCE.finditer(content)]
    if content.startswith("{") and content.endswith("}"):
        blobs.append(content)

    calls = []
    for blob in blobs:
        try:
            c = _norm_call(json.loads(blob))
        except json.JSONDecodeError:
            continue
        if c:
            calls.append(c)
    if calls:
        return calls, ""
    return [], content


class OllamaBackend(Backend):
    name = "ollama"

    def __init__(self, config: dict):
        self.host = config["ollama_host"]
        self.model = config["models"]["brain"]
        self.coder = config["models"].get("coder")
        self.keep_alive = config.get("keep_alive", "5m")
        self.label = f"ollama · brain: {self.model}" + (
            f" · coder: {self.coder}" if self.coder else "")

    @property
    def is_local(self) -> bool:
        return True

    def preflight(self) -> None:
        try:
            installed = ollama_client.list_models()
        except ollama_client.OllamaError as e:
            raise BackendError(str(e))
        for needed in [m for m in (self.model, self.coder) if m]:
            if needed not in installed:
                raise BackendError(
                    f"Required model '{needed}' is not installed. Run: ollama pull {needed}")

    def chat(self, messages, tools=None, think=None) -> dict:
        try:
            msg = ollama_client.chat(self.host, self.model, messages,
                                     tools=tools, think=think, keep_alive=self.keep_alive)
        except ollama_client.OllamaError as e:
            raise BackendError(str(e))
        calls, answer = normalize(msg)
        return {"content": answer, "tool_calls": calls}
