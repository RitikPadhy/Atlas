# Refine / tailor a resume

Goal: improve the existing `resume.md`, optionally targeting a specific job.

## Steps
1. Read `resume.md`. If it's empty or still the template, switch to `create-resume.md`.
2. If the user gave a target role or pasted a **job description (JD)**:
   - Pull the key skills, keywords, and responsibilities from the JD.
   - Reorder and reword the resume so the most relevant experience and matching
     keywords appear prominently (helps with ATS keyword screening).
3. Strengthen every bullet:
   - Lead with a strong action verb; add a concrete result or metric.
   - Remove filler ("responsible for", "helped with"), vague claims, and duplication.
   - Keep tense consistent (past for old roles, present for current).
4. Tighten length to ~one page; cut the weakest/oldest points first.
5. Sanity-check: contact info present, no typos, consistent formatting, dates align.
6. Save the improved version to `resume.md` with `write_file`.
7. Summarize what you changed and why (especially JD-driven changes).

## Notes
- Don't invent experience, employers, metrics, or skills the user doesn't have —
  ask if unsure. Honesty over keyword-stuffing.
- If tailoring to a specific company/role, also remind the user to log it in the
  tracker (`track-status.md`).
