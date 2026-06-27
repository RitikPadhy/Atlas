#!/usr/bin/env python3
"""AI Agent Center — a terminal command center backed by local Ollama models.

A resident "brain" model (qwen3:8b) reads your plain-English requests and uses
tools to get things done on your Mac: open apps/URLs/files, run shell commands,
read/write files, check system health, and delegate real coding to a specialist
model (qwen2.5-coder:7b). Destructive actions ask before they run; the brain
auto-unloads from the GPU after the keep_alive window.
"""
import datetime
import json
import os
import sys

import agent
import ollama_client
import secret_scanner
import tools as tools_mod
import ui

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        example = os.path.join(os.path.dirname(CONFIG_PATH), "config.example.json")
        raise SystemExit(
            "config.json not found. Create it from the template:\n"
            f"    cp config.example.json config.json\n"
            f"then edit it with your settings.  (template: {example})"
        )
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def confirm(question: str) -> bool:
    ans = ui.prompt(f"{ui.YELLOW}?{ui.RESET} {question} [y/N] ").strip().lower()
    return ans in ("y", "yes")


def fresh_messages(cfg: dict) -> list:
    """Start a conversation with the system prompt + today's date/time + the real
    Google account aliases, so the brain has temporal context and doesn't invent
    account names."""
    now = datetime.datetime.now().strftime("%A, %d %B %Y, %H:%M")
    msgs = [
        {"role": "system", "content": agent.SYSTEM_PROMPT},
        {"role": "system", "content": f"The current date and time is {now}."},
    ]
    g = cfg.get("google", {})
    aliases = g.get("accounts", [])
    if aliases:
        msgs.append({"role": "system", "content": (
            f"The ONLY valid Google `account` aliases are: {', '.join(aliases)} "
            f"(default: {g.get('default_account')}). Pass one of these EXACT strings — "
            f"never invent aliases like 'my work email'. To report which real email "
            f"address each maps to, or which are connected, call the google_accounts tool."
        )})
    return msgs


def main() -> None:
    cfg = load_config()
    host = cfg["ollama_host"]
    brain = cfg["models"]["brain"]
    coder = cfg["models"]["coder"]
    keep_alive = cfg.get("keep_alive", "5m")
    think = cfg.get("think_by_default", False)

    ui.banner("AI Agent Center")

    try:
        installed = ollama_client.list_models()
    except ollama_client.OllamaError as e:
        ui.error(str(e))
        sys.exit(1)

    for needed in (brain, coder):
        if needed not in installed:
            ui.error(f"Required model '{needed}' is not installed. Run: ollama pull {needed}")
            sys.exit(1)

    toolbox = tools_mod.ToolBox(cfg, confirm=confirm, notify=ui.warn)
    messages = fresh_messages(cfg)

    ui.ok(f"Brain: {ui.BOLD}{brain}{ui.RESET}  ·  coding specialist: {ui.BOLD}{coder}{ui.RESET}")
    ui.info("Type what you want. Commands: /think  /reset  /tools  /exit")
    ui.info(f"Models auto-unload from the GPU after {keep_alive} idle.")

    while True:
        try:
            raw = ui.prompt(f"\n{ui.BOLD}{ui.CYAN}atlas{ui.RESET} {ui.DIM}❯{ui.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue
        if raw in ("/exit", "/quit", "/q"):
            break
        if raw == "/reset":
            messages = fresh_messages(cfg)
            ui.info("Conversation cleared.")
            continue
        if raw == "/think":
            think = not think
            ui.info(f"Thinking mode {'on' if think else 'off'}.")
            continue
        if raw == "/tools":
            for s in tools_mod.SCHEMAS:
                fn = s["function"]
                print(f"  {ui.BOLD}{fn['name']}{ui.RESET} — {fn['description']}")
            continue

        # Secret-scan what the user typed before it ever reaches a model.
        findings = secret_scanner.scan(raw, cfg["secret_patterns"])
        if findings:
            ui.warn(f"Your message looks like it contains {len(findings)} secret(s):")
            for f in findings:
                print(f"    {ui.RED}•{ui.RESET} {ui.BOLD}{f.name}{ui.RESET} ({f.match})")
            if not confirm("Send it anyway?"):
                ui.info("Skipped.")
                continue

        messages.append({"role": "user", "content": raw})
        try:
            messages = agent.run(
                toolbox, brain, messages,
                host=host, keep_alive=keep_alive,
                max_steps=cfg.get("max_steps", 8), think=think,
            )
        except ollama_client.OllamaError as e:
            ui.error(str(e))
        except KeyboardInterrupt:
            print(f"\n{ui.DIM}(interrupted){ui.RESET}")

    ui.info(f"Models will unload from the GPU after {keep_alive} of inactivity.")


if __name__ == "__main__":
    main()
