# pdf.md — Tailored Resume PDF Generation
> Trigger: "generate PDF", "tailor my resume", "make a CV for this job", /pdf
> Requires: an evaluated job (run /evaluate first) OR JD text
> Load first: `_shared.md`, `cv.md`, `config/profile.yml`

## Step 1 — Extract JD Keywords
From the JD, rank:
- Hard skills (tools, languages, platforms): highest weight
- Domain keywords (business terms, metrics): medium weight
- Soft skills mentioned 2+ times: low weight
Top 15 keywords to inject: [list them]

## Step 2 — Rewrite CV Content

### Summary (3 lines max)
Line 1: Who + experience years
Line 2: Strongest match to THIS role (use exact JD language)
Line 3: Your differentiator

Never: "Results-driven professional with passion for data."
Always: Specific, tailored, factual.

### Experience Bullets
For each role — reorder and rewrite:
- Put most JD-relevant bullets first
- Inject JD keywords where they fit **truthfully**
- Every bullet: Action + Tool + Measured Result
- Remove bullets irrelevant to this specific role
- Do NOT fabricate. Reframe only.

Bullet formula: `[Verb] + [what you did] + [using X tool] + [measured result]`

### Skills Section
- JD-matching skills go first
- Remove skills irrelevant to this role (don't pad)
- Honest proficiency: "Python (advanced)", "SQL (intermediate)"

### Education
- Full college name, CGPA if ≥7.5, relevant coursework if directly applicable

## Step 3 — ATS Safety Check
Before generating:
- [ ] No tables, columns, or text boxes
- [ ] Standard section headers (Experience, Education, Skills)
- [ ] No graphics or photos
- [ ] All URLs plain text
- [ ] Under 1 page for <3yr experience

## Step 4 — Generate PDF
Run: `node scripts/generate-pdf.mjs --company {company} --role "{role}"`
Output: `output/{name}_{company}_{role}_{date}.pdf`

## Step 5 — Keyword Injection Summary
```
✅ Injected: [skill1, skill2, skill3]
⚠️ Not injected (you don't have it): [skill4, skill5]
💡 Consider mentioning: [adjacent skill you do have]
```

## Rules
- Never make the CV longer than 1 page for 0–2yr experience
- Never invent skills
- If no JD provided: ask for one before proceeding
