"""The orchestrator loop.

The brain model is given the user's messages plus the tool schemas. It either
answers directly or emits tool calls; we run those, feed the results back, and
loop until it produces a final answer or hits the step cap.

Local models are inconsistent about *how* they emit tool calls — some use the
native `tool_calls` field, others print `<tool_call>{...}</tool_call>` tags or a
bare JSON object in the text. `extract_tool_calls()` normalises all of these.
"""
import json
import re
from typing import Dict, List, Optional, Tuple

import ollama_client
import tools as tools_mod
import ui

SYSTEM_PROMPT = """You are the orchestrator of a terminal AI assistant running on the user's Mac.

You can call tools to get real work done: open URLs/apps/files, run shell commands,
read/write files, check the Mac's health, and delegate coding to a specialist.

Guidelines:
- When an action is needed, CALL A TOOL. Do not pretend or describe what you would do.
- For any real programming task (writing, debugging, explaining, or reviewing code),
  call `ask_coder` with a clear, self-contained brief — do not write the code yourself.
- For research or questions about current/real-world facts, use `web_search` first, then
  `web_fetch` to read the most relevant results, then synthesise an answer that cites URLs.
- For "what's on today" / daily planning, use `calendar_today` and `reminders`.
- For Google (Gmail, Calendar, Drive, Sheets) use the gmail_*/gcal_*/drive_*/sheets_*
  tools. Pass the `account` alias only if the user names one; otherwise omit it.
- The user ALSO has a separate private (non-Gmail) mailbox. For that, use mail_search /
  mail_read / mail_send — NOT the gmail_* tools. If unclear which email they mean, ask.
- run_shell and write_file ask the user to confirm, so prefer the specific tools
  (open_url, open_app, open_path, list_dir, read_file) when they fit.
- After tools have done their work, reply to the user in plain text. Be concise.
- If no tool is needed (a question, a chat), just answer directly.
- IMPORTANT: only do what your tools actually allow. If a request needs a capability
  you do NOT have a tool for, say plainly that you can't do that yet — name what's
  missing. Never pretend an action happened, invent a result, or fabricate a tool."""

_TOOL_TAG = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


def _norm(obj: Dict) -> Optional[Dict]:
    """Normalise one tool-call object to {'name', 'arguments'}."""
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


def extract_tool_calls(msg: Dict) -> Tuple[List[Dict], str]:
    """Return (tool_calls, answer_text). If tool_calls is non-empty the model
    wants to act; otherwise answer_text is its final reply."""
    native = msg.get("tool_calls")
    if native:
        calls = [c for c in (_norm(c) for c in native) if c]
        if calls:
            return calls, ""

    content = _THINK.sub("", msg.get("content") or "").strip()
    if not content:
        return [], ""

    # <tool_call>{...}</tool_call> tags
    tagged = [m.group(1) for m in _TOOL_TAG.finditer(content)]
    # ```json {...} ``` fences
    fenced = [m.group(1) for m in _FENCE.finditer(content)]
    # a whole-content bare JSON object
    bare = [content] if content.startswith("{") and content.endswith("}") else []

    calls = []
    for blob in tagged + fenced + bare:
        try:
            obj = json.loads(blob)
        except json.JSONDecodeError:
            continue
        c = _norm(obj)
        if c:
            calls.append(c)
    if calls:
        return calls, ""

    return [], content


def run(toolbox: "tools_mod.ToolBox", brain: str, messages: List[Dict],
        host: str, keep_alive: str, max_steps: int, think: bool) -> List[Dict]:
    """Run the agent loop, mutating and returning `messages`."""
    for _ in range(max_steps):
        msg = ollama_client.chat(
            host, brain, messages,
            tools=tools_mod.SCHEMAS,
            think=think,
            keep_alive=keep_alive,
        )
        calls, answer = extract_tool_calls(msg)

        if not calls:
            print(f"\n{ui.CYAN}assistant ›{ui.RESET} {answer}\n")
            messages.append({"role": "assistant", "content": answer})
            return messages

        # Record the assistant's tool-call turn in a clean, native shape.
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls],
        })

        for c in calls:
            args = c["arguments"]
            arg_preview = ", ".join(f"{k}={str(v)[:40]}" for k, v in args.items())
            ui.info(f"{ui.BOLD}{c['name']}{ui.RESET}({arg_preview})")
            result = toolbox.dispatch(c["name"], args)
            messages.append({"role": "tool", "tool_name": c["name"], "content": result})

    ui.warn(f"Reached the {max_steps}-step limit. Stopping to stay safe.")
    return messages
