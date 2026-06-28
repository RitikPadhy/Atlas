# AI Agent Center

A terminal command center backed by local **[Ollama](https://ollama.com)** models.

Open a terminal, type `ai`, and tell it what you want in plain English. A resident
**brain** model decides what to do and uses **tools** to actually do it on your Mac —
open apps, URLs and files, run shell commands, read/write files, check system health,
and hand real coding to a specialist model. Anything destructive asks before it runs,
inputs are scanned for secrets, and models auto-unload from the GPU when idle.

```
╔═════════════════╗
║ AI Agent Center ║
╚═════════════════╝
✓  Brain: qwen3:8b  ·  coding specialist: qwen2.5-coder:7b
ℹ  Type what you want. Commands: /think  /reset  /tools  /exit

⚡ atlas ❯ is my mac healthy? one line summary
ℹ  mac_health()
assistant › Your Mac is healthy — plenty of disk, stable memory, battery fine.

⚡ atlas ❯ write a python function that reverses a string
ℹ  ask_coder(task=Write a Python function that reverses a string)
⚠  → delegating to qwen2.5-coder:7b (loading the coding model)…
assistant › def reverse_string(s): return s[::-1]

⚡ atlas ❯ in one sentence with a source, what is the apple m5 chip?
ℹ  web_search(query=Apple M5 chip)
assistant › The Apple M5 is an ARM-based SoC built for AI… [source](https://…)
```

## Architecture

```
You (plain English)
   │
   ▼
BRAIN  →  qwen3:8b, resident. Reads intent, calls tools, answers.
   │      (native tool-calling; thinking mode toggled with /think)
   ├── open_url / open_app / open_path / list_dir / read_file   ← act on the Mac
   ├── run_shell / write_file                                    ← confirm first
   ├── web_search / web_fetch                                    ← research
   ├── calendar_today / reminders                                ← daily help
   ├── mac_health                                                ← system check
   └── ask_coder  →  qwen2.5-coder:7b   ← the ONE model swap, for real coding
```

**Why this shape (the decisions behind it):**

- **One resident brain does almost everything** — chat, daily help, research, deciding
  tool calls. We don't route trivial work to a smaller model, because swapping models
  costs ~5 s and the already-loaded brain answers instantly. Capability is picked by
  **specialization, not size**.
- **The coder is exposed as a tool (`ask_coder`)**, so the brain delegates real
  programming to it. That delegation is the *only* time a second model loads — a swap
  is only worth it when the capability gain is real (coding ≫ general at code).
- **qwen3:8b** is the brain because it does both jobs a brain needs: reliable native
  tool-calling *and* a toggleable thinking mode (`/think`) for harder reasoning/research.
- **Guardrails before action**: every user message is secret-scanned; `run_shell` and
  `write_file` always show the exact command/content and ask before running.
- Models **auto-unload** from the GPU after the `keep_alive` window — nothing stays
  pinned in your 16 GB once you walk away.

## Requirements

- **Ollama** running (`ollama serve`): <https://ollama.com/download>
- **Python 3.8+** — standard library only, nothing to `pip install`.
- The two models:
  ```sh
  ollama pull qwen3:8b           # the brain / orchestrator
  ollama pull qwen2.5-coder:7b   # the coding specialist
  ```

## Layout

The application code lives in **`src/`**; content and packages live at the repo root:
`backends/` (model backends), `services/` (Google, private email), `shortcuts/`,
`skills/`, and `docs/`. Only `README.md` and `.gitignore` sit loose in root.

## Install

```sh
cd ai-agent-center/src
cp config.example.json config.json   # your real config (git-ignored; never pushed)
./install.sh        # adds an `ai` alias to ~/.zshrc or ~/.bashrc
source ~/.zshrc     # or open a new terminal
ai
```

`src/config.json` holds your personal values (email address, account aliases) and is
**git-ignored** — only the placeholder `src/config.example.json` is committed.

Or run directly: `python3 src/ai_agent.py`.

## Commands

| Command | Action |
| ------- | ------ |
| (plain text) | Tell the brain what you want |
| `/` | Menu of commands + shortcuts (live dropdown) |
| `@` | Skills & capability packs (live dropdown) |
| `@<pack>` | Load a capability pack's tools (e.g. `@google`, `@mac`) |
| `@<skill>` | Engage a skill's playbook + its tools (e.g. `@job-tracker`) |
| `/<shortcut>` | Run a saved prompt (e.g. `/summary`, `/health`) |
| `/packs` | List capability packs and which are loaded |
| `/think` | Toggle qwen3's thinking mode (deeper reasoning, slower) |
| `/tools` | List the tools currently loaded for the brain |
| `/reset` | Clear the conversation (and reset loaded packs) |
| `/exit` `/q` | Quit (models auto-unload) |
| `Ctrl-C` | Interrupt |

**Capability packs:** to keep the model sharp, only a lean **core** tool set is always
loaded; specialized tools (Google, private email, Mac, job-tracker) live in *packs* that
load on demand — when you type `@<pack>`, or when a shortcut/skill declares it needs them.
See [`docs/capability-packs.md`](docs/capability-packs.md).

## Tools the brain can call

| Tool | What it does | Confirms? |
| ---- | ------------ | --------- |
| `open_url` | Open a URL in the browser (`Google Chrome` by default) | no |
| `open_app` | Launch a macOS app | no |
| `open_path` | Open a file/folder in Finder / default app | no |
| `list_dir` | List a directory | no |
| `read_file` | Read a file's contents | no |
| `write_file` | Write text to a file | **yes** |
| `run_shell` | Run any shell command | **yes** |
| `web_search` | Search the web (DuckDuckGo, no API key) | no |
| `web_fetch` | Fetch a page and return its readable text | no |
| `calendar_today` | Today's events from macOS Calendar | no¹ |
| `reminders` | Open reminders from macOS Reminders | no¹ |
| `mac_health` | Models loaded, memory, disk, battery, uptime, top CPU | no |
| `gmail_search` / `gmail_send` | Search / send Gmail (multi-account) | send: **yes** |
| `gcal_events` / `gcal_create_event` | Google Calendar list / create | create: **yes** |
| `drive_search` | Search Google Drive files | no |
| `sheets_read` / `sheets_write` | Read / write Google Sheets ranges | write: **yes** |
| `ask_coder` | Delegate a coding task to `qwen2.5-coder:7b` (swaps model) | no |

¹ On first use, macOS asks you to grant Calendar/Reminders access in
**System Settings → Privacy & Security → Automation**.

The Google tools live in **`services/Google/`** and need a one-time OAuth setup
(`pip install -r src/requirements.txt`, a free Cloud project, then
`python3 services/Google/authorize.py <account>` per account — see
[`services/Google/README.md`](services/Google/README.md)). Until that's done the
Google tools just report they aren't set up; the rest of the agent works regardless.

## Configuration — `config.json`

| Key | Meaning |
| --- | ------- |
| `provider` | Which model backend to use (`ollama` today; add more in `backends/`) |
| `models.brain` / `models.coder` | The resident brain and the coding specialist |
| `keep_alive` | How long a model stays in the GPU after last use (`"5m"`) |
| `think_by_default` | Start with qwen3 thinking mode on/off |
| `max_steps` | Safety cap on tool calls per request |
| `browser_app` | Default browser for `open_url` |
| `max_tool_output_chars` | Truncate large tool output before feeding it back |
| `secret_patterns` | `{ "name", "regex" }` rules for the secret scanner |

## Project layout

| Path | Responsibility |
| ---- | -------------- |
| `src/ai_agent.py` | REPL entry point — input, secret scan, `/` shortcuts, `@` skills & packs |
| `src/agent.py` | The orchestrator loop (provider-agnostic) + system prompt |
| `src/tools.py` | The tools (verbs), capability-pack registry, `ask_coder` delegation |
| `src/ollama_client.py` | `ollama list` + tool-calling `/api/chat` (used by the Ollama backend) |
| `src/secret_scanner.py` · `src/ui.py` | Secret detection · terminal colors/prompts |
| `src/config.json` · `src/install.sh` | Your settings (git-ignored) · adds the `ai` alias |
| `backends/` | Model backends behind one interface (`ollama`, `claude`) — repo root |
| `services/` | Google + private-email API clients — repo root |
| `shortcuts/` · `skills/` | `/`-invoked saved prompts · `@`-invoked playbooks — repo root |
| `docs/` | Architecture & how-to docs (capability packs, providers, roadmap) |

## Switching models / providers

This runs on **local Ollama models** (`provider: "ollama"` in `config.json`). The
model layer is pluggable via a **Backend** interface (`backends/`), so the underlying
model can be swapped later without touching tools, skills, shortcuts, services, or
guardrails. If/when you want to switch, see **[`docs/switching-providers.md`](docs/switching-providers.md)**.

## Notes & limitations

- A local 8B is **not** as reliable as a frontier model at tool-calling. The step cap,
  the confirmation prompts, and the secret scanner exist because of this — keep tasks
  reasonably scoped and watch what `run_shell` is about to do.
- Web search uses DuckDuckGo's HTML endpoint (no API key). It can rate-limit or change
  markup; if results stop parsing, that's why.
- Built and tested on Apple **M5 / 16 GB**. One model is resident at a time; a coder
  delegation briefly loads the second, then it unloads via `keep_alive`.
