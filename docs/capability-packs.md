# Architecture: Capability Packs (load-on-demand for tools)

Status: **implemented** (Phases 1–3). Tools are grouped into packs; a lean core is
always loaded; packs load on demand via `@<pack>` or a shortcut/skill `requires:`
line; loading is provider-aware (`tool_loading` in config). Phase 4 (auto-router)
is the only remaining optional piece.

## The problem it solves
Tools are sent to the model on **every** request (the `tools` list — "box #3"),
regardless of what the user typed. Adding tools globally therefore taxes *every*
prompt twice: more tokens per request, and more options the model must choose
among. On a local 8B that degrades both speed and tool-selection accuracy. Skills
(markdown) are already load-on-demand; tools are not. As skills/services grow, the
always-on tool list grows unbounded.

## The principle
**Load-on-demand, applied to everything.** The system already does this for *models*
(keep_alive load/unload) and *skill instructions* (`@`). Extend it to *tools*: keep
the model's resident tool set minimal; everything else is retrievable, not resident.
(Same idea as RAG for knowledge, or swapping specialist models.)

## The model: two tiers

### Tier 1 — Core (always on, ~8–10 tools)
The universal verbs the brain needs regardless of task:
`run_shell`, `read_file`, `write_file`, `list_dir`, `open_url`, `open_app`,
`open_path`, `web_search`, `web_fetch`, `ask_coder` (local only).
This is the *entire* always-resident tool surface — flat forever.

### Tier 2 — Capability packs (loaded on demand)
Each pack bundles **instructions + its own tools + its own data**, loaded only when
needed. Services and skills both become packs — one concept:

| Pack | Tools | Notes |
| ---- | ----- | ----- |
| `google` | gmail_search, gmail_send, gcal_events, gcal_create_event, drive_search, sheets_read, sheets_write, google_accounts | from `services/Google` |
| `email` | mail_search, mail_read, mail_send | private IMAP (`services/Private_Emails`) |
| `mac` | mac_health, reminders, calendar_today | local system |
| `job-tracker` | job_add, job_update, job_list | + the 11 guides in `skills/job-tracker` |

(`list_accounts` spans google+email — keep it in core, or expose in both. Minor; decide at build.)

## How a pack gets loaded
1. **Explicit** — `@google`, `@job-tracker`, etc. Deterministic; the *harness* loads the
   pack (not the model), so there's no model-guessing step. **Default, most reliable —
   the right fit for a local 8B (explicit > implicit).**
2. **Declared dependency** — a shortcut or skill states the packs it needs; invoking it
   loads the **union**. This is how cross-pack tasks work:
   ```
   shortcuts/summary.md   requires: [google, email]   → loads both packs
   skills/job-tracker/SKILL.md   requires: [job-tracker]
   ```
   Recurring multi-pack tasks therefore *become* declared shortcuts/skills — which is
   exactly what they're for.
3. **Auto-router (optional, later)** — a cheap classifier pre-loads a pack when a freehand
   prompt obviously matches ("any unread mail?" → load `google`). Convenience layer only;
   it's a model-judgment step that can misfire on an 8B, so it never replaces (1)/(2).

**Lifetime:** a loaded pack stays active for the rest of the conversation (so a
job-tracking session keeps its tools); `/reset` returns to core-only.

## Provider-awareness (this is also the Claude story)
The loading logic lives **above the `Backend`**, so it's provider-agnostic — Claude
drops in unchanged. But the *need* differs, so make it configurable per provider:

| Provider | Tool loading |
| -------- | ------------ |
| `ollama` (local 8B) | lean core + explicit/declared packs — **essential** |
| `claude` (Opus 4.8, 1M ctx, strong tool-calling) | load all packs by default, or map packs onto Claude's native **tool-search** — the constraint relaxes |

This is *forward-compatible*, not a throwaway: Claude Code itself runs on deferred
tools + tool-search — the same pattern. Packs now → tool-search later, cleanly.

## What changes in code (high level — for the build, not now)
- **Tool registry by pack:** replace the flat `tools.SCHEMAS` with groups —
  `CORE` + a `{pack_name: [schemas]}` map. The implementations stay in `ToolBox`.
- **Active-pack state** in the REPL/agent loop: tracks which packs are loaded for the
  current conversation; `agent.run` sends `CORE + active packs` to `backend.chat`.
- **`@pack` loading** in `ai_agent.py`: typing `@google` (or invoking a skill) activates
  that pack for the conversation.
- **`requires:` declaration:** a small frontmatter/field in shortcut `.md` files and skill
  `SKILL.md`; the harness parses it and activates those packs on invocation.
- **Provider config:** `config.json` per-provider tool-loading mode (`lean` vs `all`).
- **`/packs` command + dropdown:** list available packs and which are active (mirrors `/`).

## Phased build plan
1. ✅ **Group tools into packs** + active-pack tracking; `@<pack>` loads a pack; default =
   core only; `@job-tracker` loads the job pack. (`tools.py` `_PACK_OF`/`PACKS`/`active_schemas`.)
2. ✅ **`requires:` for shortcuts/skills** so `/summary` loads `google`+`email`, `/health`→`mac`.
3. ✅ **Provider-aware loading** — `config.tool_loading` (`ollama: lean`, `claude: all`);
   `ask_coder` auto-excluded on non-local backends.
4. ⬜ **Optional auto-router** — cheap classifier pre-loads obvious packs from freehand prompts.

## Honest tradeoffs
- **UX friction:** "any unread email?" typed freehand won't work until `google` is loaded —
  you'd invoke `@google`, use a shortcut that declares it, or add the auto-router. Real cost.
- **Don't go fully dynamic on the 8B:** a `load_capability` tool the *model* must call adds
  an indirection step it can fumble. Explicit `@`/`requires` (harness-loaded) avoids it.
- **Migration effort:** regrouping today's 28 global tools into packs is a real refactor,
  done incrementally so nothing breaks.
- **Cross-pack tools** (`list_accounts`) need a home — core, or duplicated across packs.

## Why this is the right end-state
- Skills/services **can never bloat the model**, by construction — only the small core is
  always-on.
- The system scales to dozens of packs with a flat resident surface.
- It's correct at every model tier — tuned tight for the 8B, relaxed for Claude — and
  aligns with Anthropic's own tool-search scaling pattern.
