# skill-gap.md — Skill Gap Analysis Mode
> Trigger: "what skills am I missing", "what should I learn", "skill gap", /skills
> Load first: `_shared.md`, `cv.md`, `config/profile.yml`, `data/scan_results.json` (if exists)

## What This Does
Analyzes your skills against what the market is actually asking for.
Uses either recent scan results (real data) or general market knowledge.
Tells you specifically what to learn and in what order.

---

## Step 1 — Skill Frequency Analysis

If `data/scan_results.json` exists:
- Parse all job snippets from the scan
- Count keyword frequency across all matching jobs
- Rank by: (frequency in JDs) × (absence from candidate's CV)

If no scan data:
- Use general knowledge of top skills for candidate's target roles in Indian market

---

## Step 2 — Gap Matrix

```
## Skill Gap Analysis

Your target roles: {from profile.yml}
Jobs analyzed: {N from scan_results or "general market"}

CRITICAL GAPS (in >50% of JDs, you don't have)
────────────────────────────────────────────────
Skill            In JDs    Time to learn    Best resource
dbt              68%       3–4 weeks        dbt Learn (free)
BigQuery         54%       2–3 weeks        Google Cloud free tier
Airflow          48%       4–6 weeks        Astronomer tutorials

USEFUL GAPS (in 20–50% of JDs, you don't have)
────────────────────────────────────────────────
Spark            35%       6–8 weeks        Databricks community
Looker           28%       2–3 weeks        Looker free training

NICE TO HAVE (in <20% of JDs)
────────────────────────────────────────────────
Snowflake        18%       2–3 weeks
dbt Cloud        15%       1 week (after dbt core)

YOUR STRENGTHS (you have, market wants)
────────────────────────────────────────────────
Python           91%    ✅ Strong
SQL              88%    ✅ Strong
pandas           72%    ✅ Good
Metabase         41%    ✅ Present
n8n/automation   22%    ✅ Differentiator — mention prominently
```

---

## Step 3 — Learning Roadmap

Based on the gap matrix, produce a prioritized 3-month plan:

```
## 90-Day Skill-Up Plan

Month 1 — Highest ROI gap: {top skill}
  Week 1–2: {specific resource + what to build}
  Week 3–4: {mini project to prove the skill}
  Proof of skill: {what to add to GitHub/CV}

Month 2 — Second gap: {skill}
  [same format]

Month 3 — Third gap + consolidation
  [same format]

Quick wins (under 1 week each):
- {skill}: {specific 1-day tutorial}

Don't learn all of these. Pick one. Finish it. Add it to your CV.
Depth on one skill beats surface knowledge on five.
```

---

## Step 4 — What Not to Learn

Just as important:
- Skills that appear in <10% of JDs for your target role → not worth the time right now
- Skills that require a job to learn (Spark at scale, production ML) → get the job first
- Certifications that don't signal skill → AWS Cloud Practitioner is not worth your time for data analyst roles; AWS Data Analytics Specialty is

---

## Output after analysis
Offer: "Want me to log these gaps as a study plan in your tracker?"
