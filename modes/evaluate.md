# evaluate.md — Single Job Evaluation Mode
> Trigger: user pastes a job URL or JD text
> Load first: `_shared.md`, `cv.md`, `config/profile.yml`

## Step 1 — Extract Job Data
If URL: navigate and extract title, company, location, salary, experience required, full JD.
If page is dead (404, "position closed"): tell the user immediately and stop.
If JD text pasted: parse the same fields, note any missing ones.

## Step 2 — Block G: Ghost Job Check
Flag if 2+ of these are true:
- No salary disclosed
- JD under 150 words
- Posted over 90 days ago
- Mostly generic language, no specific tools/metrics
- No company LinkedIn or <10 employees
- Identical JD reposted on 5+ boards

Output: **Legitimacy: High / Medium / Low / Suspicious** with 1-line reason.
If Suspicious: warn prominently. Continue evaluation but flag clearly.

## Step 3 — Score (10 dimensions, weighted)
See `_shared.md` for weights. For each dimension: sub-score 0–5 + 1-sentence reason.
Weighted total → Grade (A/B/C/D/F).

## Step 4 — 6-Block Report

### Block A — Role Summary
```
Role: {title} at {company}
Location: {city} | {remote/hybrid/onsite}
Salary: {LPA or "Not disclosed"}
Experience: {X–Y years}
Legitimacy: {High/Medium/Low/Suspicious}

[2–3 sentences: what this role actually does day-to-day]
```

### Block B — CV Match
```
Score: {X.X}/5.0 | Grade: {A/B/C/D/F}

✅ Strong matches: [3–5 specific skills/experiences that align]
⚠️  Partial matches: [2–3 things partially there]
❌ Gaps: [hard requirements the candidate lacks — be specific]

Overall: [1–2 honest sentences on fit level]
```

### Block C — Level & Positioning
- Is the role too senior or too junior?
- Is the title misleading (e.g., "Data Analyst" that's really MIS)?
- How should the candidate position their application?

### Block D — Compensation Analysis
```
Listed salary: {X–Y LPA or "Not disclosed"}
Candidate target: {from profile.yml}
Assessment: {Within range / Below / Above / Unknown}
Market benchmark: {X–Y LPA for this role+tier+city}
In-hand estimate: {~X LPA/month}
ESOP: {mentioned/not mentioned}
Negotiation note: [1 sentence on leverage]
```

### Block E — Tailoring Recommendations
```
Top 5 JD keywords to inject:
1. {keyword} → place in: {summary / bullet / skills}
2–5. ...

Resume tweak (specific, not generic):
[actual bullet point to rewrite or section to adjust]
```

### Block F — Interview Preview
```
Likely format: [X rounds]
Technical round: [SQL? Python? Case study?]

2 high-probability questions:
Q1: {question} → STAR angle: {which candidate story fits}
Q2: {question} → STAR angle: {which candidate story fits}

48-hour prep priority: [what to review before applying]
```

## Step 5 — Final Recommendation
```
Recommendation: APPLY NOW / APPLY WITH TWEAKS / BORDERLINE / DO NOT APPLY
Reason: [2 sentences]
Next action: [specific]
```

## Step 6 — Offer to Log
"Want me to add this to your tracker?" If yes: append to `data/pipeline.json`.

## Tone Rules
- Direct and specific. No "great opportunity" or "exciting role."
- If bad fit: say "this is not a match because X" — not "you may want to consider..."
- Quantify: "you match 4/6 required tools" > "good technical match"
