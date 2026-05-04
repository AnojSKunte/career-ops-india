# prep.md — Interview Preparation Mode
> Trigger: "prep me for [company]", "interview tomorrow", /prep
> Load first: `_shared.md`, `cv.md`, plus evaluation report if it exists in reports/

## Step 1 — Identify the Interview
Extract or ask: company, role, which round, days until interview, case study expected?

## Step 2 — Company Brief
```
Company: {name} | Stage: {funding} | Founded: {year}
Business: [1 sentence plain English]
Revenue model: [how they make money]
Recent news: [last 6 months — funding, layoffs, launches]
Hiring known for: [e.g., "strong SQL rounds", "culture-heavy HR screen"]
Team context: [data team, growth team, product team?]
```

## Step 3 — Round-Specific Prep

### HR Screen
20–30 min. Focus on: story, salary expectation, why this company.
1. "Tell me about yourself" → 90-sec version: current role → what you built → why here
2. "Why [Company]?" → MUST be specific. Research their product.
3. "Why leaving?" → growth pull, not push away
4. "Current CTC + expectation?" → Know your number. Don't anchor low.
Key: don't go deep technical. Save energy.

### Technical Round (SQL/Python/Analytics)
**SQL patterns to know:**
- Window functions: ROW_NUMBER(), RANK(), LAG(), LEAD()
- CTEs vs subqueries (when to use each)
- Self joins (cohorts, retention, org hierarchy)
- Date functions: DATEDIFF, DATE_TRUNC
- GROUP BY + HAVING vs WHERE

**Python/pandas:**
- groupby, merge, pivot_table, apply, explode
- Always: .head(), .describe(), .info() first — show you explore before assuming

**Case study framework:**
1. Clarify: which segment, platform, baseline period?
2. Segment: user type, channel, geography, device
3. Hypothesize: external (holiday, outage) vs internal (feature change, bug)
4. Validate: what data would you pull first?

### Hiring Manager Round
Focus: "can this person do the job and grow here?"
Use STAR+R for all behavioral questions:
- Situation → Task → Action → Result → Reflection (what you learned)

## Step 4 — Questions to Ask Them
Prepare 3–4. Bad candidates have none.
1. "What's the biggest data/analytics pain point you're solving in the next 6 months?"
2. "How does data team interact with product — data-driven or data-informed here?"
3. "What does a successful first 90 days look like?"
Do NOT ask: "What are growth opportunities?" (too generic)
Do NOT ask about salary in technical rounds.

## Step 5 — 48-Hour Study Plan
Day 1: SQL window functions (2hr) + 3 case studies from company domain + review 3 STAR stories
Day 2: Company research + practice "tell me about yourself" out loud + rest
Day of: review questions to ask, have CV open, test audio 10 min early
