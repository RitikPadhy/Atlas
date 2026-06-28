# Offers & negotiation

Goal: record offers accurately, compare them, and support negotiation.

## Record an offer
- `job_update(id, status="Offer", offer={"base": ..., "equity": ..., "bonus": ..., "currency": ..., "deadline": "<date>", "status": "received", "notes": "..."})`.
- Set `next_action="respond to offer"`, `next_action_date=<deadline minus buffer>`.

## Compare offers
- `job_list(status="Offer")` to pull all offers. Lay them side by side: base, equity,
  bonus, total, location, deadline, and fit-to-goals (from `config/profile.md`).
- Give a clear read of trade-offs; recommend, but the decision is the user's.

## Negotiate
- Anchor on the user's target/minimum from `config/profile.md` and any competing offers.
- Draft a polite, specific counter (what to ask for, the justification, a fallback).
- Offer to send it via `gmail_send` / `mail_send` (confirms first).

## Close out
- On accept: `job_update(id, status="Accepted")`, and offer to set start-date reminders
  (`gcal_create_event`) and to withdraw from other active apps (`job_update(other_id, status="Withdrawn")`).

## Notes
- Never invent numbers or deadlines — record only what the user provides.
