# Job Tracker — create & refine resumes and track job applications

## When to use this skill
Engage this skill when the user's request involves their **job search**: writing or
building a **resume / CV**, **refining / tailoring** a resume to a role, or
**tracking job applications** (where they applied, status, next steps, interviews).
Trigger words: resume, CV, cover letter, apply/applied, application, job, role,
interview, offer, recruiter, job search, "tailor my resume", "track my jobs".

## How to use it
1. Read this SKILL.md, then read the specific guide file for the task below.
2. Follow that guide's steps. Ask the user for any details you don't have.
3. The working data lives in `resume.md` and `applications.md` — read them before
   editing, and use the `write_file` tool to save changes (it will confirm first).

## Files in this skill
| File | Purpose |
| ---- | ------- |
| `SKILL.md` | This manifest — when to use the skill and what each file does. |
| `create-resume.md` | Step-by-step guide to build a resume from scratch into `resume.md`. |
| `refine-resume.md` | Guide to improve/tailor an existing `resume.md` to a target role. |
| `resume.md` | The user's working resume (the live document you create & edit). |
| `applications.md` | The job-application tracker (a table of companies/roles/status). |
| `track-status.md` | Guide to read and update `applications.md`. |

## Routing the user's request
- "make/build/write my resume" → follow `create-resume.md`.
- "improve / tailor / fix my resume", or they paste a job description → follow `refine-resume.md`.
- "I applied to…", "what's my status", "update X to interview", "what's pending" → follow `track-status.md`.
