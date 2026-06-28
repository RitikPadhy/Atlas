"""Claude (Anthropic) backend — cloud models via the official `anthropic` SDK.

Lazy-imports `anthropic` so the package is only required when this provider is
actually used (the Ollama setup keeps working without it). Translates the
canonical OpenAI/Ollama-style message history to and from Anthropic's
content-block shape, and normalizes the reply to {content, tool_calls}.

Model defaults to claude-opus-4-8 (adaptive-thinking-only family; no sampling
params, no assistant prefill — none of which this backend sends).
"""
import os

from .base import Backend, BackendError


def _to_anthropic(messages):
    """Canonical messages -> (system_str, anthropic_messages).

    Assistant tool-call turns become `tool_use` content blocks; the `tool`-role
    results that follow become a single `tool_result` user message, matched to
    the tool_use blocks by order (we synthesise consistent ids per request).
    """
    system_parts, out = [], []
    i, n, counter = 0, len(messages), 0
    while i < n:
        m = messages[i]
        role = m.get("role")
        if role == "system":
            c = m.get("content")
            if c:
                system_parts.append(c if isinstance(c, str) else str(c))
            i += 1
        elif role == "user":
            out.append({"role": "user", "content": m.get("content", "")})
            i += 1
        elif role == "assistant" and m.get("tool_calls"):
            blocks = []
            text = (m.get("content") or "").strip()
            if text:
                blocks.append({"type": "text", "text": text})
            ids = []
            for tc in m["tool_calls"]:
                fn = tc.get("function", tc)
                cid = f"toolu_{counter}"
                counter += 1
                ids.append(cid)
                blocks.append({"type": "tool_use", "id": cid,
                               "name": fn.get("name"), "input": fn.get("arguments") or {}})
            out.append({"role": "assistant", "content": blocks})
            i += 1
            results, k = [], 0
            while i < n and messages[i].get("role") == "tool" and k < len(ids):
                results.append({"type": "tool_result", "tool_use_id": ids[k],
                                "content": messages[i].get("content", "")})
                i += 1
                k += 1
            if results:
                out.append({"role": "user", "content": results})
        elif role == "assistant":
            out.append({"role": "assistant", "content": m.get("content", "")})
            i += 1
        else:  # stray tool message with no preceding tool_calls — skip
            i += 1
    return "\n\n".join(p for p in system_parts if p), out


def _to_anthropic_tools(tools):
    out = []
    for t in tools or []:
        fn = t.get("function", t)
        out.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
        })
    return out


class ClaudeBackend(Backend):
    name = "claude"

    def __init__(self, config: dict):
        c = config.get("claude", {})
        self.model = c.get("model", "claude-opus-4-8")
        self.max_tokens = int(c.get("max_tokens", 16000))
        self.api_key_env = c.get("api_key_env", "ANTHROPIC_API_KEY")
        self.label = f"claude · {self.model}"
        self._client = None

    def preflight(self) -> None:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            raise BackendError("The 'anthropic' package isn't installed. Run: pip install anthropic")
        if not os.environ.get(self.api_key_env):
            raise BackendError(
                f"No Anthropic API key. Get one at console.anthropic.com (this is the "
                f"pay-per-use API — separate from a Claude.ai subscription), then:\n"
                f"    export {self.api_key_env}=sk-ant-...")

    def _client_(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        return self._client

    def chat(self, messages, tools=None, think=None) -> dict:
        # `think` is intentionally ignored: enabling adaptive thinking with tool use
        # requires echoing thinking blocks back unchanged, which our canonical history
        # doesn't preserve. Opus 4.8 handles these tasks well without it.
        system, msgs = _to_anthropic(messages)
        kwargs = {"model": self.model, "max_tokens": self.max_tokens, "messages": msgs}
        if system:
            kwargs["system"] = system
        atools = _to_anthropic_tools(tools)
        if atools:
            kwargs["tools"] = atools
        try:
            resp = self._client_().messages.create(**kwargs)
        except Exception as e:
            raise BackendError(f"Claude API error: {e}")

        text_parts, calls = [], []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                calls.append({"name": block.name, "arguments": block.input or {}})
        return {"content": "".join(text_parts).strip(), "tool_calls": calls}
