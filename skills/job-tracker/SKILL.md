# Job Tracker — run a job search end to end: discover, apply, track, interview, offer
requires: job-tracker

## When to use this skill
Engage for anything in the user's **job search**: finding roles, evaluating a job
against their profile, writing/tailoring a **resume or cover letter**, **applying**,
**tracking applications**, **follow-ups**, **company research**, **interview prep**
and logging, **offers/negotiation**, and **retrospective analytics**.
Triggers: job, role, apply/applied, application, resume, CV, cover letter, recruiter,
interview, offer, negotiate, "tailor my resume", "track my jobs", "what's my pipeline".

## How the data is stored (read this)
- **The application pipeline is tool-managed** — use the `job_add`, `job_update`, and
  `job_list` tools. NEVER hand-edit the pipeline file; the tools keep it from being
  corrupted. Each application record can carry its interviews and offer inline.
- **Other files** live under this skill's folder (the absolute path is given to you
  when the skill is invoked). Read/write them with `read_file` / `write_file`:
  - `config/profile.md` — the user's profile (target roles, locations, preferences).
  - `data/resume.md` — the working master resume.
  - `data/star-stories.md` — reusable STAR interview stories.
  - `companies/<name>.md` — research notes per company.
  - `output/` — generated artifacts (tailored resumes, cover letters).
  - `templates/` — starting templates (committed; copy, don't overwrite).
- Personal data (`data/`, `output/`, `companies/`) is git-ignored — never committed.

## Application status pipeline (canonical)
`Wishlist → Applied → Screen → Interview → Offer → Accepted` — or `Rejected` /
`Withdrawn` at any point. Use these exact status words with `job_update`.

## Files (guides) and when to use each
| Request | Guide to read |
| ------- | ------------- |
| "find / search for jobs", build a wishlist | `guides/discover.md` |
| "is this job a good fit?", score a JD | `guides/evaluate.md` |
| "make / build my resume" | `guides/create-resume.md` |
| "tailor / improve my resume" (to a JD) | `guides/refine-resume.md` |
| "write a cover letter" | `guides/cover-letter.md` |
| "I applied to X", "track this", "what's my pipeline" | `guides/apply-and-track.md` |
| "follow up", "what's pending / overdue" | `guides/follow-up.md` |
| "research <company>" | `guides/research-company.md` |
| "prep me for an interview", log an interview | `guides/interview.md` |
| "I got an offer", compare/negotiate offers | `guides/offers.md` |
| "how's my search going", funnel stats | `guides/retrospective.md` |

## How to work
1. Read the matching guide above, then follow its steps.
2. Ask the user for any details you don't have (don't invent companies, dates, comp).
3. Use the user's other tools where the guide says to — `web_search`/`web_fetch`
   (discovery, research), `gmail_search`/`mail_search`/`gmail_send` (recruiter mail,
   follow-ups), `gcal_events`/`gcal_create_event` and `reminders` (interviews, deadlines).
4. For pipeline changes, always go through `job_add`/`job_update`/`job_list`.

## First-time setup to mention if nothing exists yet
If `config/profile.md` is missing, offer to create it from `config/profile.example.md`;
if `data/resume.md` is missing, route to `guides/create-resume.md`.
