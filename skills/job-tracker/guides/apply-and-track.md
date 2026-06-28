# Apply & track applications

Goal: log applications and keep the pipeline accurate. The pipeline is **tool-managed** —
always use `job_add` / `job_update` / `job_list`, never hand-edit a file.

## Always
- Use today's date (it's in the system context) for dates.
- Statuses are exactly: Wishlist, Applied, Screen, Interview, Offer, Accepted, Rejected, Withdrawn.

## Common requests
- **"I applied to <Company> for <Role>"** →
  `job_add(company, role, jd_url=?, source=?, status="Applied", date_applied=<today>, resume_version=?)`,
  then suggest a follow-up date (~profile cadence, default 10 days) and note it via
  `job_update(id, next_action="follow up", next_action_date=<date>)`.
- **"Add <Company> to my wishlist"** → `job_add(..., status="Wishlist")`.
- **"Move <Company> to screen/interview/offer/rejected"** →
  find the id with `job_list`, then `job_update(id, status="...")` and refresh next_action.
- **"What's my pipeline / show my applications"** → `job_list()` (shows funnel counts +
  every app); `job_list(status="Interview")` to filter.
- **"Log an interview for <Company>"** → `job_update(id, add_interview={round, date, type, interviewer, notes})`
  (or see `interview.md`).
- **"I got an offer from <Company>"** → `job_update(id, status="Offer", offer={...})` (see `offers.md`).

## Notes
- One record per application. Confirm the id with `job_list` before updating.
- Don't invent companies, dates, or outcomes — ask the user.
