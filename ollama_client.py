"""Thin wrapper around the Ollama CLI (model discovery) and HTTP API (chat).

Uses only the Python standard library so the tool runs with a stock
`python3` and no `pip install` step.
"""
import json
import subprocess
import urllib.error
import urllib.request
from typing import Dict, List, Optional


class OllamaError(RuntimeError):
    pass


def list_models() -> List[str]:
    """Return installed model names, parsed from `ollama list`."""
    try:
        out = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, check=True,
        ).stdout
    except FileNotFoundError:
        raise OllamaError("`ollama` is not installed or not on your PATH.")
    except subprocess.CalledProcessError as e:
        raise OllamaError(f"`ollama list` failed: {e.stderr.strip()}")

    models = []
    for line in out.splitlines()[1:]:  # skip the header row
        line = line.strip()
        if line:
            models.append(line.split()[0])  # first column is NAME
    return models


def chat(
    host: str,
    model: str,
    messages: List[Dict],
    tools: Optional[List[Dict]] = None,
    think: Optional[bool] = None,
    keep_alive: str = "5m",
    timeout: int = 300,
) -> Dict:
    """Non-streaming POST /api/chat. Returns the assistant `message` dict,
    which may contain `content` and/or `tool_calls`."""
    body: Dict = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": keep_alive,
    }
    if tools:
        body["tools"] = tools
    if think is not None:
        body["think"] = think

    req = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        # Some models reject the `think` field; retry once without it.
        if think is not None and "think" in detail.lower():
            return chat(host, model, messages, tools, None, keep_alive, timeout)
        raise OllamaError(f"chat request failed ({e.code}): {detail}")
    except urllib.error.URLError as e:
        raise OllamaError(
            f"Could not reach Ollama at {host}. Is `ollama serve` running? ({e})"
        )
    if "error" in data:
        raise OllamaError(data["error"])
    return data.get("message", {})


def unload(host: str, model: str) -> None:
    """Best-effort: ask Ollama to drop a model from memory immediately."""
    payload = json.dumps({"model": model, "keep_alive": 0}).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except Exception:
        pass  # the keep_alive timer will reclaim the GPU regardless
