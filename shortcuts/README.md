# Shortcuts

Saved prompts you trigger with a slash command. Type `/summary` in the agent and
it runs `summary.md` as the task; the brain carries it out using its tools.

## How they work
- **Filename = command.** `summary.md` → `/summary`, `weekly.md` → `/weekly`.
- The file's **contents are the instruction** sent to the agent (plain English).
- Anything you type after the command is appended as extra context:
  `/draft reply to John about the invoice` → runs `draft.md` + "reply to John …".
- `/shortcuts` lists all available shortcuts (the first line of each file is its blurb).

## Add a new one
Just drop a `.md` file here. Tips for reliable results on a local model:
- Spell out **which tools to call** (e.g. "call `gmail_search` with `newer_than:7d`").
- Say exactly **what output you want** (format, grouping, length).
- Tell it **how to handle failures** ("if an account isn't reachable, note it and continue").

## Included
- `summary.md` — today's emails across all accounts, grouped & summarized.
