# Refine / tailor a resume to a job

Goal: produce a job-specific resume in `output/`, leaving the master `data/resume.md` intact.

## Steps
1. Read `data/resume.md`. If empty/template, switch to `create-resume.md`.
2. Get the target job (URL → `web_fetch`, pasted JD, or a tracked app's `jd_url`).
   Pull its key skills, keywords, and responsibilities.
3. Tailor a COPY:
   - Reorder/reword so the most relevant experience and matching keywords surface first
     (helps ATS keyword screening) — honestly, never keyword-stuff with skills the user lacks.
   - Strengthen bullets (action verb + result/metric); cut the weakest/oldest first.
   - Keep ~one page, consistent tense, no typos, contact info present.
4. `write_file` the tailored version to `output/resume-<company>-<role>.md`.
5. Tell the user what changed and why (especially JD-driven changes).
6. Remind them to record which version they used when they apply
   (`job_update(id, resume_version="resume-<company>-<role>.md")`).

## Notes
- Do not modify `data/resume.md` here — that's the master. Tailored copies go in `output/`.
