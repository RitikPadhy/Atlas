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
import warnings

# The Google libs pull in urllib3, which warns about LibreSSL on system Python.
# It's harmless noise — keep it out of the chat output.
warnings.filterwarnings("ignore", message=".*OpenSSL.*")

import agent
import ollama_client
import secret_scanner
import tools as tools_mod
import ui

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.styles import Style
    _HAVE_PTK = True
    # Make the completion dropdown blend into the terminal: default background,
    # terminal foreground, the selected row as native reverse-video, dim meta.
    _MENU_STYLE = Style.from_dict({
        "completion-menu": "bg:default",
        "completion-menu.completion": "bg:default fg:default",
        "completion-menu.completion.current": "reverse",
        "completion-menu.meta.completion": "bg:default fg:ansibrightblack",
        "completion-menu.meta.completion.current": "reverse",
        "scrollbar.background": "bg:default",
        "scrollbar.button": "bg:ansibrightblack",
    })
except Exception:
    _HAVE_PTK = False

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
    email_aliases = list(cfg.get("email", {}).get("accounts", {}).keys())
    if aliases or email_aliases:
        msgs.append({"role": "system", "content": (
            f"Valid Google `account` aliases: {', '.join(aliases) or 'none'} "
            f"(default: {g.get('default_account')}). Private (IMAP) email aliases: "
            f"{', '.join(email_aliases) or 'none'}. Use these EXACT alias strings — never "
            f"invent names. When the user asks which email/accounts are connected, call "
            f"list_accounts (it covers BOTH Google and the private email)."
        )})
    return msgs


SHORTCUTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shortcuts")


def list_shortcuts() -> list:
    if not os.path.isdir(SHORTCUTS_DIR):
        return []
    return sorted(f[:-3] for f in os.listdir(SHORTCUTS_DIR)
                  if f.endswith(".md") and not f.upper().startswith("README"))


def load_shortcut(name: str):
    """Return a shortcut's prompt text, or None if it doesn't exist."""
    path = os.path.join(SHORTCUTS_DIR, f"{name}.md")
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        return f.read().strip()


def shortcut_summary(name: str) -> str:
    body = load_shortcut(name) or ""
    first = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
    return first[:70] + "…" if len(first) > 70 else first


def slash_options() -> list:
    """(command, description) pairs for the live completion menu — built-ins + shortcuts."""
    opts = [("/think", "toggle thinking mode"), ("/reset", "clear conversation"),
            ("/tools", "list tools"), ("/exit", "quit")]
    opts += [("/" + n, shortcut_summary(n)) for n in list_shortcuts()]
    return opts


if _HAVE_PTK:
    class SlashCompleter(Completer):
        """Live dropdown: as soon as the line starts with '/', suggest matching
        commands/shortcuts and filter them as more letters are typed."""
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if not text.startswith("/"):
                return
            for opt, meta in slash_options():
                if opt.startswith(text):
                    yield Completion(opt, start_position=-len(text), display_meta=meta)


def make_session():
    """A prompt_toolkit session with live slash-completion, or None to use plain input."""
    if _HAVE_PTK and sys.stdin.isatty():
        return PromptSession(completer=SlashCompleter(),
                             complete_while_typing=True, style=_MENU_STYLE)
    return None


def read_line(session, prompt_text: str) -> str:
    if session is not None:
        return session.prompt(ANSI(prompt_text))
    return input(prompt_text)


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
    session = make_session()
    prompt_text = f"\n{ui.BOLD}{ui.CYAN}atlas{ui.RESET} {ui.DIM}❯{ui.RESET} "

    ui.ok(f"Brain: {ui.BOLD}{brain}{ui.RESET}  ·  coding specialist: {ui.BOLD}{coder}{ui.RESET}")
    hint = "type / for a live menu" if session else "type / and Enter for the menu"
    ui.info(f"Type what you want. Shortcuts & commands: {hint}.")
    ui.info(f"Models auto-unload from the GPU after {keep_alive} idle.")

    while True:
        try:
            raw = read_line(session, prompt_text).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        if raw.startswith("/"):
            cmd, _, extra = raw[1:].partition(" ")
            cmd, extra = cmd.lower(), extra.strip()
            if cmd == "":  # bare "/" → show everything available
                ui.info("Commands: /think  /reset  /tools  /exit")
                names = list_shortcuts()
                if names:
                    ui.info("Shortcuts:")
                    for n in names:
                        print(f"  {ui.BOLD}/{n}{ui.RESET} — {shortcut_summary(n)}")
                else:
                    ui.info("No shortcuts yet — add a .md file in shortcuts/.")
                continue
            if cmd in ("exit", "quit", "q"):
                break
            if cmd == "reset":
                messages = fresh_messages(cfg)
                ui.info("Conversation cleared.")
                continue
            if cmd == "think":
                think = not think
                ui.info(f"Thinking mode {'on' if think else 'off'}.")
                continue
            if cmd == "tools":
                for s in tools_mod.SCHEMAS:
                    fn = s["function"]
                    print(f"  {ui.BOLD}{fn['name']}{ui.RESET} — {fn['description']}")
                continue
            if cmd in ("shortcuts", "help"):
                names = list_shortcuts()
                if names:
                    ui.info("Shortcuts (type /<name>):")
                    for n in names:
                        print(f"  {ui.BOLD}/{n}{ui.RESET} — {shortcut_summary(n)}")
                else:
                    ui.info("No shortcuts yet. Add a .md file in the shortcuts/ folder.")
                continue
            # Otherwise: a user-defined shortcut (shortcuts/<cmd>.md)?
            body = load_shortcut(cmd)
            if body is None:
                ui.warn(f"Unknown command or shortcut: /{cmd}")
                names = list_shortcuts()
                if names:
                    ui.info("Available shortcuts: " + ", ".join("/" + n for n in names))
                continue
            ui.info(f"Running shortcut /{cmd}…")
            raw = body if not extra else f"{body}\n\nExtra instruction from the user: {extra}"
            # fall through — `raw` is now the shortcut's prompt

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
