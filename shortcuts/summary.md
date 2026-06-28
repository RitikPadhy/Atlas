requires: google, email

Summarize all the emails I received TODAY across all of my accounts.

Do this:
- Call `list_accounts` first to see which accounts are connected.
- For EACH Google account, call `gmail_search` with query `newer_than:1d`.
- For the private email, call `mail_search` with `since_days: 1`.

Then write the summary with this EXACT structure — you MUST output one section per
account, even if it has zero messages:

  ## Gmail (personal) — <N> message(s)
  - <sender> · <subject> · <≈5-word gist>
  ...

  ## Private (admin@unexplo.com) — <N> message(s)
  - <sender> · <subject> · <≈5-word gist>
  ...

Rules:
- NEVER omit an account. If an account had no messages, still print its header with
  "0 message(s)" and "(nothing today)".
- If an account couldn't be reached, print its header with "(could not access: <reason>)".
- After both sections, add a one-line FLAGS note for anything important/time-sensitive
  (bills, deadlines, replies expected, security alerts), or "Flags: none".
