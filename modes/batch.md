# batch.md — Batch Job Evaluation Mode
> Trigger: multiple URLs, "batch these", "evaluate all", /batch
> Load first: `_shared.md`, `cv.md`, `config/profile.yml`

## What This Does
Quick-scores multiple jobs. Surfaces top matches fast. Filters noise.
Use after /scan when you have 10–40 jobs to triage.

## Quick Score (5 of 10 dimensions — speed optimized)
1. Role-skill match (25%)
2. Salary fit (20%)
3. Tech stack overlap (15%)
4. Experience fit (5%)
5. Legitimacy check (2%)

Skip: company research, JD quality, growth trajectory (too slow for batch).
Label all batch scores as estimates. Run /evaluate for full report.

## Output Table
```
## Batch Results — {N} jobs evaluated

| # | Grade | Company | Role | Location | Salary | Why |
|---|---|---|---|---|---|---|
| 1 | A | Razorpay | Data Analyst | Bangalore | 14–18 LPA | Strong SQL+Python, Tier 1 |
...

Filtered out (F/Suspicious): {N} jobs — [company names]
```

## Post-Batch Actions
🔴 Apply today (Grade A): [list]
🟡 Tailor and apply (Grade B): [list]
🟠 Thin pipeline only (Grade C): [list]
⛔ Skip (D/F): [list with 1-line reason]

Offer: "Add all A/B to tracker as to_apply?"

## Batch Limits
- Up to 30 jobs: process all at once
- 30–60: two passes, show results after each
- 60+: warn and suggest pre-filtering by location or salary
