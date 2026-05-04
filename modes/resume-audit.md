# resume-audit.md — Resume Audit Mode (no job needed)
> Trigger: "audit my resume", "review my CV", "is my CV good", /audit
> Load first: `_shared.md`, `cv.md`

## What This Does
Audits your CV cold — without a specific job. Catches structural problems,
ATS issues, weak bullets, missing quantification, and Indian-market red flags.
Run this before you start applying.

---

## Step 1 — ATS Parse Test
Simulate how an ATS reads your CV:
- Can every section be identified by its header? (Experience, Education, Skills)
- Are there any tables, columns, text boxes, or graphics that would break parsing?
- Are contact details on a single parseable line?
- Is the file likely to be under 1MB as PDF?

Output: **ATS Safety: Pass / Warn / Fail** with specific issues.

---

## Step 2 — Structural Audit

Check and report:
```
Length: {N lines} → {1 page for <3yr experience — flag if longer}
Summary: {present / missing / weak}
Bullet count per role: {N} → {3–6 bullets recommended}
Quantification: {N/total bullets have numbers} → flag if below 50%
Education: {CGPA present? Full college name?}
Skills section: {present / missing / hidden in bullets}
URLs: {LinkedIn / GitHub present?}
Gaps: {any unexplained employment gaps?}
```

---

## Step 3 — Bullet Quality Analysis

For each bullet point, classify:
- **Strong**: verb + tool + measured outcome (e.g., "Built ETL pipeline in Python reducing report time by 60%")
- **Weak**: vague verb, no tool, no outcome (e.g., "Worked on data projects")
- **Fix needed**: has potential but missing a number or specific tool

Output:
```
Strong bullets: {N}
Weak bullets:   {N} — [list them with suggested rewrites]
```

For each weak bullet, provide:
```
Original: "Worked on dashboard development"
Rewrite:  "Built 6 operational dashboards in Metabase tracking [metric], reducing manual report requests by [N] per week"
Missing info needed: [what number or context should you fill in]
```

---

## Step 4 — Indian Market Red Flags

Check for:
- Photo included → remove
- Date of birth, marital status, address → remove
- Objective statement (not summary) → replace with summary
- References on CV → remove ("available on request" is also unnecessary)
- Generic skills everyone lists: "MS Office", "Communication", "Teamwork" → remove
- Full home address → city only is fine
- Old email format (e.g., @yahoo, @rediffmail) → flag, suggest Gmail
- CGPA below 7.0 on CV → consider removing

---

## Step 5 — Keyword Gap Analysis (general, not job-specific)

For the candidate's target roles, list the top 10 most common JD keywords
they should have in their CV (based on role type from profile.yml).
Flag which ones are missing.

For Data Analyst / Analytics Engineer roles, the must-haves are:
SQL, Python, data visualization, ETL, dashboards, business intelligence,
stakeholder management, A/B testing, metrics, data pipeline

```
Present: {list}
Missing: {list — prioritized by importance}
```

---

## Step 6 — Score + Action Plan

```
## Resume Audit Score

ATS Safety:     {score}/10
Structure:      {score}/10
Bullet Quality: {score}/10
Quantification: {score}/10
Keywords:       {score}/10

Overall: {total}/50 → {letter grade}

Top 3 things to fix TODAY (ordered by impact):
1. {most impactful fix — specific}
2. {second most impactful}
3. {third}

After fixing: run /audit again to verify.
```
