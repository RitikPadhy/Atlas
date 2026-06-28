# Retrospective / funnel analytics

Goal: show how the search is going and what to adjust.

## Steps
1. `job_list()` — it returns funnel counts per status plus every application.
2. Compute and present the funnel and conversion rates:
   - Applied → Screen, Screen → Interview, Interview → Offer (as % where counts allow).
   - Response rate (any reply / total applied).
   - Median time sitting in each stage, if dates allow (rough is fine).
3. Surface patterns:
   - Which sources (`source` field) convert best.
   - Roles/companies getting traction vs. silence.
   - Bottleneck stage (where most applications stall).
4. Give 2–3 concrete suggestions (e.g. "screens aren't converting → interview prep",
   "low response rate → tailor resumes more / widen sourcing").

## Notes
- Be honest about small sample sizes — call out when there's too little data to conclude.
- Don't invent numbers; derive everything from the pipeline.
