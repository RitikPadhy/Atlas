# Discover roles

Goal: find relevant openings and add the good ones to the pipeline as `Wishlist`.

## Steps
1. Read `config/profile.md` for target roles, location, seniority, and wishlist
   companies. If it's missing, offer to set it up first.
2. Use `web_search` with focused queries built from the profile, e.g.
   "<role> <location> jobs", "<company> careers <role>", "<role> remote hiring".
   Run a few queries; vary the angle (role title, company, seniority).
3. For promising hits, optionally `web_fetch` the posting to confirm it's real and
   matches (location, level, must-haves).
4. Present a short list: company · role · location · link · one-line why-it-fits.
5. For each one the user likes, add it with `job_add(company, role, jd_url=..., source="search", status="Wishlist")`.
6. Offer to evaluate fit (`guides/evaluate.md`) on any of them.

## Notes
- Don't fabricate postings or links — only surface what search actually returned.
- Flag stale-looking listings; suggest `web_fetch` to verify before applying.
