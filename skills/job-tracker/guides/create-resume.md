# Create a resume (from scratch)

Goal: produce a clean master resume at `data/resume.md`.

## Steps
1. Check `data/resume.md`. If it already has real content, ask whether to start over
   or switch to refining (`refine-resume.md`).
2. Read `config/profile.md` for context. Collect anything missing (ask in batches):
   - Name, location, email, phone, links (LinkedIn/GitHub/portfolio).
   - Target role.
   - Experience: company, title, dates, 2–4 bullets each.
   - Education, skills (grouped), optional projects/certs/awards.
3. Write strong bullets: **action verb + what you did + impact/metric**
   (e.g. "Cut API latency 40% by adding a Redis cache layer").
4. Keep it ~one page; most recent and most relevant first.
5. Start from `templates/resume-template.md` and `write_file` the result to `data/resume.md`.
6. Summarize what you wrote; offer to tailor it to a specific job (`refine-resume.md`).

## Notes
- Don't invent employers, dates, or metrics — ask the user.
