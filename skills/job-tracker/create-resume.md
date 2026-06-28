# Create a resume (from scratch)

Goal: produce a clean, one-page-style resume in `resume.md`.

## Steps
1. Read `resume.md` — if it already has real content (not the template), ask whether
   to start over or switch to refining (`refine-resume.md`).
2. Collect the user's details (ask for whatever is missing, one batch at a time):
   - Name, location, email, phone, LinkedIn/GitHub/portfolio.
   - Target role / field they're applying for.
   - Work experience: company, title, dates, and 2–4 bullet points each.
   - Education: degree, institution, year, notable scores/coursework.
   - Skills (grouped: languages, tools, frameworks).
   - Optional: projects, certifications, awards.
3. Write strong bullets: **action verb + what you did + impact/metric**.
   e.g. "Cut API latency 40% by adding a Redis cache layer."
4. Keep it concise — aim for one page; most recent and most relevant first.
5. Save the result to `resume.md` with `write_file`.
6. Tell the user what you wrote and offer to tailor it to a specific job
   (hand off to `refine-resume.md`).

## Output format for `resume.md`
Use this structure (Markdown):
```
# <Name>
<location> · <email> · <phone> · <links>

## Summary
<2–3 line positioning statement for the target role>

## Experience
### <Title>, <Company> — <dates>
- <impact bullet>

## Education
### <Degree>, <Institution> — <year>

## Skills
- Languages: ...
- Tools/Frameworks: ...

## Projects (optional)
### <Project> — <one line + link>
- <impact bullet>
```
