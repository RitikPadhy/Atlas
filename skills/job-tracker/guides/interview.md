# Interview prep & logging

Two jobs: prepare the user before a round, and capture what happened after.

## Prep (before)
1. Identify the company and role (from the tracked app via `job_list`, or ask).
2. Read `companies/<company>.md` if it exists; otherwise offer `research-company.md` first.
3. Read `data/star-stories.md` (reusable stories) and `data/resume.md`.
4. Produce a prep pack:
   - Likely questions for this role/level (behavioural + role-specific/technical).
   - For each behavioural question, **match a STAR story** from `data/star-stories.md`
     (if none fits, draft one with the user and append it to that file).
   - 2–3 questions the user should ask them (pull from the company research).
   - Logistics check: confirm time/format; offer `gcal_create_event` for the slot.

## Log (after)
- Capture the round on the application:
  `job_update(id, add_interview={"round": "...", "date": "<today>", "type": "phone/onsite/technical", "interviewer": "...", "notes": "questions asked + how it went", "outcome": "pending/advanced/rejected"})`.
- If they advanced, set `job_update(id, status="Interview")` (or "Offer"); set the next_action.
- Suggest a thank-you note (draft + `gmail_send`/`mail_send`, which confirm first).

## Notes
- Keep STAR stories truthful and metric-driven; reuse across interviews.
