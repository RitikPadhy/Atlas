# Evaluate a job's fit

Goal: score how well a specific job matches the user, so they apply where it counts.

## Steps
1. Get the job description — from a URL the user gives (`web_fetch` it), pasted text,
   or a tracked application's `jd_url`.
2. Read `config/profile.md` and `data/resume.md` for the user's background and goals.
3. Pull the job's key requirements: must-haves, nice-to-haves, seniority, location,
   comp (if listed).
4. Assess fit across: skills match, seniority match, location/authorization, comp,
   and goal alignment (from the profile's "optimizing for" line).
5. Give a **letter grade A–F** with a 2–3 line rationale, then:
   - the top 2–3 strengths to lead with,
   - the top 1–2 gaps (and whether they're dealbreakers),
   - a recommendation: apply / apply if tailored / skip.
6. If they want to proceed, route to `refine-resume.md` (tailor) then `apply-and-track.md`.

## Notes
- Be honest about gaps; don't inflate the grade. A clear "skip" saves their time.
- Don't claim skills/experience the resume doesn't show.
