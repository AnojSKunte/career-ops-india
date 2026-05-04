# _shared.md — Shared Context
> Load at the start of every mode. Defines scoring, Indian market context, output formats.

## Indian Market Context

### Salary
- All salaries in **LPA (Lakhs Per Annum)** = CTC (Cost to Company)
- In-hand ≈ 65–72% of CTC after PF, tax, health insurance
- Variable pay at startups: 10–30% of CTC; ESOPs vest over 4 years (1-year cliff)
- "Competitive salary" with no number = ask before investing time in application

### Company Tiers
| Tier | Examples | Salary (0–2yr) |
|---|---|---|
| Tier 1 Product | Razorpay, CRED, Zepto, Swiggy, PhonePe | 12–22 LPA |
| Tier 2 Growth | Series A–B, mid-size SaaS | 8–15 LPA |
| Tier 3 IT/Service | TCS, Infosys, Wipro | 4–8 LPA |
| MNC India | Google, Microsoft, Amazon | 15–30+ LPA |

### Role Titles (India-specific)
- "Data Analyst" = SQL + Excel + dashboards (not ML unless specified)
- "Analytics Engineer" = dbt + SQL + pipelines (growing, rare)
- "Business Analyst" = product BA or consulting BA — clarify from JD
- "MIS Executive" = NOT a data role — flag this to the candidate
- "Data Scientist" at Indian startups often = analyst work + minor ML

### Interview Process (Typical Indian Startup)
1. HR screen (20–30 min) → 2. Technical/SQL test → 3. Hiring manager → 4. Founder (at small startups)
- Turnaround: 1–3 weeks at startups, 4–8 weeks at MNCs

---

## Scoring Framework (1.0–5.0, 10 Dimensions)

| # | Dimension | Weight |
|---|---|---|
| 1 | Role-skill match | 25% |
| 2 | Salary fit | 20% |
| 3 | Tech stack overlap | 15% |
| 4 | Growth trajectory | 10% |
| 5 | Company tier/health | 10% |
| 6 | Location/remote | 5% |
| 7 | JD quality | 5% |
| 8 | Experience fit | 5% |
| 9 | Resume gap | 3% |
| 10 | Legitimacy (Block G) | 2% |

**Grade Scale:**
- A (4.5–5.0): Apply today
- B (4.0–4.4): Apply with tailored CV
- C (3.5–3.9): Apply if pipeline is thin
- D (3.0–3.4): Significant gaps
- F (<3.0): Do not apply

---

## Tracker Entry Format

Append to `data/pipeline.json`:
```json
{
  "id": "auto-increment",
  "company": "",
  "role": "",
  "grade": "A/B/C/D/F",
  "score": 0.0,
  "status": "to_apply",
  "source": "greenhouse|lever|ashby|naukri|linkedin|manual",
  "url": "",
  "salary_listed": "",
  "location": "",
  "date_found": "YYYY-MM-DD",
  "date_applied": null,
  "next_action": "",
  "notes": ""
}
```

Status flow: `to_apply → applied → hr_screen → technical → final_round → offer → accepted`
Dead ends: `rejected`, `withdrawn`, `expired`
