# Skills

Multi-step **playbooks** the agent follows for a whole area of work (richer than a
single-shot `shortcuts/` prompt). Each skill is a folder with a `SKILL.md` manifest
plus supporting files (guides, templates, and working data).

## How you invoke them
Skills are invoked **explicitly with `@`** (shortcuts use `/`):
```
@job-tracker create my resume
@job-tracker            # engages the skill; it asks what you want to do
@                       # lists all skills
```
Typing `@` shows a live dropdown of skills (same as `/` for shortcuts). When you
invoke `@<name>`, the agent injects that skill's `SKILL.md` playbook directly into
the message, then follows it — reading the relevant guide and the skill's data files
(via `read_file`) and updating them. The injection makes invocation reliable: the
model doesn't have to *discover* the skill, it's handed the playbook.

## Add a skill
1. Make a folder: `skills/<name>/`.
2. Add `SKILL.md` whose **first line** is `# <Name> — <one-line purpose>` (that line
   is what the agent sees in its skill list), followed by **when to use it**, the
   **files** and their roles, and **how to route** requests.
3. Add the supporting files (guides + any working data files).

## Included
- `job-tracker/` — create & refine resumes and track job applications.
