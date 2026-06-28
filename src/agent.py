"""The orchestrator loop — provider-agnostic.

It talks only to a Backend (see backends/), which returns a normalized reply:
{"content": str, "tool_calls": [{"name", "arguments"}, ...]}. The loop runs any
tool calls, feeds results back, and repeats until a final answer or the step cap.
Conversation history is the OpenAI/Ollama-style message format; the backend
translates to/from its provider's shape.
"""
from typing import Dict, List

import tools as tools_mod
import ui

SYSTEM_PROMPT = """You are the orchestrator of a terminal AI assistant running on the user's Mac.

You can call tools to get real work done: open URLs/apps/files, run shell commands,
read/write files, check the Mac's health, search the web, manage email and Google
services, and delegate coding to a specialist.

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


def run(toolbox: "tools_mod.ToolBox", backend, messages: List[Dict],
        tools: List[Dict], max_steps: int, think: bool) -> List[Dict]:
    """Run the agent loop, mutating and returning `messages`. `tools` is the
    resolved schema list for this turn (core + whatever packs are active)."""
    for _ in range(max_steps):
        reply = backend.chat(messages, tools=tools, think=think)
        calls = reply.get("tool_calls") or []

        if not calls:
            answer = (reply.get("content") or "").strip()
            print(f"\n{ui.CYAN}assistant ›{ui.RESET} {answer}\n")
            messages.append({"role": "assistant", "content": answer})
            return messages

        # Record the assistant's tool-call turn in canonical (OpenAI/Ollama) shape.
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": c["name"], "arguments": c["arguments"]}}
                           for c in calls],
        })

        for c in calls:
            args = c["arguments"]
            arg_preview = ", ".join(f"{k}={str(v)[:40]}" for k, v in args.items())
            ui.info(f"{ui.BOLD}{c['name']}{ui.RESET}({arg_preview})")
            result = toolbox.dispatch(c["name"], args)
            messages.append({"role": "tool", "tool_name": c["name"], "content": result})

    ui.warn(f"Reached the {max_steps}-step limit. Stopping to stay safe.")
    return messages
