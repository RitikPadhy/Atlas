# Write a cover letter

Goal: a tailored cover letter in `output/`, grounded in the user's real background.

## Steps
1. Read `config/profile.md` and `data/resume.md`. Get the target job (URL/paste/tracked).
2. Identify the company's mission/role's top 2–3 requirements (`web_fetch` the posting,
   and optionally `companies/<name>.md` if research exists).
3. Draft from `templates/cover-letter-template.md`:
   - Opening: why this company + the single strongest fit reason (specific, not generic).
   - Body: 1–2 achievements (real metrics) mapped to the job's top requirements.
   - Close: what you'd bring + thank-you.
4. Keep it under one page; mirror the JD's language honestly.
5. `write_file` to `output/cover-<company>-<role>.md` and show it to the user.

## Notes
- Never invent achievements or claim experience not in the resume — ask if unsure.
- If they'll email it, offer to send via `gmail_send` / `mail_send` (those confirm first).
