# Track job application status

Goal: keep `applications.md` accurate and answer questions about the user's pipeline.

## Always
- Read `applications.md` first to get the current table.
- When you change it, write the FULL updated table back with `write_file`.
- Use today's date (it's provided in the system context) for "Date Applied" and
  when computing follow-up dates.

## Common requests
- **"I applied to <Company> for <Role>"** → add a new row: Status `Applied`,
  Date Applied = today, suggest a Next Action ("follow up in ~10 days").
- **"Add <Company> to my wishlist"** → new row with Status `Wishlist`.
- **"Update <Company> to interview / offer / rejected"** → change that row's Status
  and refresh Next Action accordingly.
- **"What's my status / show my pipeline"** → summarize: counts per status, then list
  rows grouped by status (active ones first).
- **"What needs action / what's pending"** → list rows whose Next Action is due or
  overdue relative to today, and anything stuck in a stage too long.

## Keep it clean
- One row per application. Remove the example row once a real one exists.
- Don't invent companies, dates, or outcomes — ask the user if a detail is missing.
