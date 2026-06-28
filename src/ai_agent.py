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

# This file lives in src/. The package folders (backends, services) and content
# folders (shortcuts, skills) live in the repo root, one level up — put the root on
# the import path so `import backends` and the lazy `import services` resolve.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import agent
import backends
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
    skills = list_skills()
    skill_names = ", ".join(f"@{n}" for n, _, _ in skills) or "none"
    packs = ", ".join(f"@{p}" for p in tools_mod.PACKS) or "none"
    msgs.append({"role": "system", "content": (
        f"Capabilities load on demand. You only see the tools currently loaded; more exist "
        f"behind capability packs the user loads with @<name>. Skills (playbooks + tools): "
        f"{skill_names}. Packs (tools only): {packs}. If a request needs a capability you don't "
        f"have a tool for right now, DON'T guess — tell the user to load it, e.g. "
        f"'I need the email tools — run @google (or @email) and ask again.' When a skill is "
        f"invoked its playbook is injected into the message; just follow it."
    )})
    return msgs


# shortcuts/ and skills/ live in the repo root (not in src/).
SHORTCUTS_DIR = os.path.join(_ROOT, "shortcuts")
SKILLS_DIR = os.path.join(_ROOT, "skills")


def list_skills() -> list:
    """Return (name, purpose, abs_skill_md_path) for each skill folder with a SKILL.md."""
    out = []
    if not os.path.isdir(SKILLS_DIR):
        return out
    for name in sorted(os.listdir(SKILLS_DIR)):
        folder = os.path.join(SKILLS_DIR, name)
        if not os.path.isdir(folder):
            continue
        skill_md = next((os.path.join(folder, f) for f in os.listdir(folder)
                         if f.lower() == "skill.md"), None)
        if not skill_md:
            continue
        purpose = ""
        with open(skill_md) as fh:
            for line in fh:
                line = line.strip().lstrip("#").strip()
                if line:
                    purpose = line
                    break
        out.append((name, purpose, skill_md))
    return out


def load_skill(name: str):
    """Return (skill_md_text, skill_folder_abs) for a skill, or None if missing."""
    info = next((s for s in list_skills() if s[0] == name), None)
    if not info:
        return None
    _, _, skill_md = info
    with open(skill_md) as f:
        return f.read().strip(), os.path.dirname(skill_md)


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


def parse_requires(text: str):
    """Pull `requires: a, b` lines out of a shortcut/skill body.
    Returns (pack_names, body_without_those_lines)."""
    reqs, kept = [], []
    for line in text.splitlines():
        if line.strip().lower().startswith("requires:"):
            reqs += [p.strip() for p in line.split(":", 1)[1].replace(",", " ").split()]
        else:
            kept.append(line)
    return reqs, "\n".join(kept).strip()


def shortcut_summary(name: str) -> str:
    _, body = parse_requires(load_shortcut(name) or "")
    first = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
    return first[:70] + "…" if len(first) > 70 else first


def slash_options() -> list:
    """(command, description) pairs for the live completion menu — built-ins + shortcuts."""
    opts = [("/think", "toggle thinking mode"), ("/packs", "capability packs"),
            ("/reset", "clear conversation"), ("/tools", "tools loaded now"), ("/exit", "quit")]
    opts += [("/" + n, shortcut_summary(n)) for n in list_shortcuts()]
    return opts


if _HAVE_PTK:
    class SlashCompleter(Completer):
        """Live dropdown: as soon as the line starts with '/', suggest matching
        commands/shortcuts and filter them as more letters are typed."""
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if text.startswith("/"):
                for opt, meta in slash_options():
                    if opt.startswith(text):
                        yield Completion(opt, start_position=-len(text), display_meta=meta)
            elif text.startswith("@"):
                seen = set()
                for name, purpose, _ in list_skills():
                    seen.add(name)
                    opt = "@" + name
                    if opt.startswith(text):
                        yield Completion(opt, start_position=-len(text), display_meta=purpose)
                for p in tools_mod.PACKS:
                    if p in seen:
                        continue
                    opt = "@" + p
                    if opt.startswith(text):
                        yield Completion(opt, start_position=-len(text), display_meta="capability pack")


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
    keep_alive = cfg.get("keep_alive", "5m")
    think = cfg.get("think_by_default", False)
    provider = cfg.get("provider", "ollama")
    tool_mode = cfg.get("tool_loading", {}).get(provider, "lean")  # "lean" | "all"

    ui.banner("AI Agent Center")

    backend = backends.get_backend(cfg)
    try:
        backend.preflight()
    except backends.BackendError as e:
        ui.error(str(e))
        sys.exit(1)

    toolbox = tools_mod.ToolBox(cfg, confirm=confirm, notify=ui.warn)
    messages = fresh_messages(cfg)

    def initial_packs():
        # "all" loads every pack up front (fine for big-context models like Claude);
        # "lean" starts core-only and loads packs on demand via @ / shortcut requires.
        return set(tools_mod.PACKS) if tool_mode == "all" else set()
    active_packs = initial_packs()

    session = make_session()
    prompt_text = f"\n{ui.BOLD}{ui.CYAN}atlas{ui.RESET} {ui.DIM}❯{ui.RESET} "

    ui.ok(backend.label)
    enter = "" if session else " and Enter"
    ui.info(f"Type what you want.  /{enter} = commands & shortcuts · @{enter} = skills & packs")
    if backend.is_local:
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
            if cmd == "":  # bare "/" → menu
                ui.info("Commands: /think  /packs  /reset  /tools  /exit")
                for n in list_shortcuts():
                    print(f"  {ui.BOLD}/{n}{ui.RESET} — {shortcut_summary(n)}")
                continue
            if cmd in ("exit", "quit", "q"):
                break
            if cmd == "reset":
                messages = fresh_messages(cfg)
                active_packs = initial_packs()
                ui.info("Conversation cleared; capability packs reset.")
                continue
            if cmd == "think":
                think = not think
                ui.info(f"Thinking mode {'on' if think else 'off'}.")
                continue
            if cmd == "packs":
                ui.info("Capability packs (load with @<name>):")
                for p in tools_mod.PACKS:
                    state = f"{ui.GREEN}● active{ui.RESET}" if p in active_packs else f"{ui.DIM}○ idle{ui.RESET}"
                    print(f"  {ui.BOLD}@{p}{ui.RESET}  {state}")
                continue
            if cmd == "tools":
                loaded = tools_mod.active_schemas(active_packs, is_local=backend.is_local)
                ui.info(f"Tools available to the model now ({len(loaded)}):")
                for s in loaded:
                    fn = s["function"]
                    print(f"  {ui.BOLD}{fn['name']}{ui.RESET} — {fn['description']}")
                if set(tools_mod.PACKS) - active_packs:
                    ui.info("More load on demand — see /packs.")
                continue
            if cmd in ("shortcuts", "help"):
                for n in list_shortcuts():
                    print(f"  {ui.BOLD}/{n}{ui.RESET} — {shortcut_summary(n)}")
                continue
            # a user-defined shortcut (shortcuts/<cmd>.md)?
            raw_body = load_shortcut(cmd)
            if raw_body is None:
                ui.warn(f"Unknown command or shortcut: /{cmd}")
                names = list_shortcuts()
                if names:
                    ui.info("Available shortcuts: " + ", ".join("/" + n for n in names))
                continue
            reqs, body = parse_requires(raw_body)
            active_packs |= {p for p in reqs if p in tools_mod.PACKS}
            ui.info(f"Running /{cmd}" + (f" (loaded: {', '.join(reqs)})" if reqs else "") + "…")
            raw = body if not extra else f"{body}\n\nExtra instruction from the user: {extra}"
            # fall through — `raw` is now the shortcut's prompt

        elif raw.startswith("@"):
            name, _, task = raw[1:].partition(" ")
            name, task = name.strip(), task.strip()
            if name == "":  # bare "@" → list skills + packs
                skills = list_skills()
                if skills:
                    ui.info("Skills (@<name> → playbook + its tools):")
                    for n, purpose, _ in skills:
                        print(f"  {ui.BOLD}@{n}{ui.RESET} — {purpose}")
                ui.info("Packs (@<name> → just the tools):")
                for p in tools_mod.PACKS:
                    print(f"  {ui.BOLD}@{p}{ui.RESET}" + ("  (active)" if p in active_packs else ""))
                continue
            loaded = load_skill(name)
            if loaded is not None:
                content, folder = loaded
                reqs, content = parse_requires(content)
                if name in tools_mod.PACKS:
                    active_packs.add(name)
                active_packs |= {p for p in reqs if p in tools_mod.PACKS}
                ui.info(f"Engaging skill @{name}…")
                raw = (
                    f"{content}\n\n---\n"
                    f"The user has invoked the '{name}' skill; its playbook is above. The skill's "
                    f"files are in this folder: {folder} — use read_file (with the absolute path) to "
                    f"open any guide or data file the playbook references. "
                    f"User's request: {task or '(none yet — briefly ask what they want to do in this skill)'}"
                )
                # fall through
            elif name in tools_mod.PACKS:
                active_packs.add(name)
                ui.info(f"Loaded @{name} pack.")
                if not task:
                    continue  # tools loaded; wait for the next prompt
                raw = task
                # fall through
            else:
                ui.warn(f"Unknown skill or pack: @{name}")
                opts = sorted({s[0] for s in list_skills()} | set(tools_mod.PACKS))
                if opts:
                    ui.info("Available: " + ", ".join("@" + o for o in opts))
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
        tools = tools_mod.active_schemas(active_packs, is_local=backend.is_local)
        try:
            messages = agent.run(
                toolbox, backend, messages, tools,
                max_steps=cfg.get("max_steps", 12), think=think,
            )
        except backends.BackendError as e:
            ui.error(str(e))
        except KeyboardInterrupt:
            print(f"\n{ui.DIM}(interrupted){ui.RESET}")

    if backend.is_local:
        ui.info(f"Models will unload from the GPU after {keep_alive} of inactivity.")


if __name__ == "__main__":
    main()
