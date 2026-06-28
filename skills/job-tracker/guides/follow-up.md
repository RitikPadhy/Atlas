# Follow-ups

Goal: surface what needs action and help the user nudge at the right time.

## What's pending / overdue
1. `job_list()` to get every application with its `next_action` / `next_action_date`.
2. Compare `next_action_date` to today (in the system context). Report:
   - **Overdue** (date ≤ today) first, then **due soon**, then the rest.
   - Anything stuck in one status too long (e.g. Applied with no movement past the cadence).
3. For each, suggest the concrete next step (follow up, send thank-you, withdraw).

## Check for replies
- Use `gmail_search` (e.g. `from:<company> newer_than:14d`) and `mail_search` to see if a
  recruiter replied. If so, suggest updating status (`job_update`) and clearing/advancing next_action.

## Draft & schedule
- Offer to draft a follow-up or thank-you email and send it with `gmail_send` / `mail_send`
  (these confirm first). Keep it short, specific, and polite.
- Offer to set a reminder/calendar nudge: `gcal_create_event` for a deadline, or note the
  next_action_date with `job_update(id, next_action=..., next_action_date=...)`.

## Notes
- Don't send anything without the user confirming the recipient and text.
