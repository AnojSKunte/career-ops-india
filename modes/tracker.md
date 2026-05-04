# tracker.md — Application Pipeline Tracker
> Trigger: "I applied", "got a call", "rejected", "show pipeline", /tracker, /pipeline
> Data file: `data/pipeline.json`

## Status Flow
`to_apply → applied → hr_screen → technical → final_round → offer → accepted`
Dead ends: `rejected`, `withdrawn`, `expired`

## Commands

**"I applied to [company]"**
Update: to_apply → applied. Set date_applied. Ask: "Any notes? Referral? Tailored CV?"

**"Got a call from [company]"**
Update: → hr_screen. Ask when. Offer to run /prep.

**"Had technical round"**
Update: → technical. Ask how it went, what was asked. Store in notes.

**"Got rejected by [company]"**
Update: → rejected. Ask which stage + any feedback.
Then run rejection pattern analysis (see below).

**"Got an offer"**
Update: → offer. Ask for CTC breakdown. Offer to run /negotiate.

**"Show my pipeline" / /pipeline**
Display full dashboard (below).

## Pipeline Dashboard
```
## Application Pipeline — {date}

Summary: Active: {N} | Offers: {N} | Rejected: {N} | To Apply: {N}

🔴 Needs action today
[jobs where next_action overdue OR to_apply older than 14 days]

🟡 In progress
| Company | Role | Stage | Last update | Next action |

✅ Offers
[company, CTC, deadline]

⛔ Last 5 rejections [company, stage, date]

Conversion: Applied→HR: {%} | HR→Technical: {%} | Technical→Offer: {%}
```

## Rejection Pattern Analysis
After each rejection:
- Was grade below B? → system predicted this. Recalibrate filters.
- 3rd+ technical rejection? → SQL/Python fundamentals need work. Run /prep.
- 3rd+ HR rejection? → story or salary expectation misaligned.

## Stale Alert
Application in "applied" for 21+ days with no update:
"No response from [Company] in 21 days. Mark as ghosted, follow up, or leave open?"

## Data Rules
- Never delete entries — only update status
- Always set date_applied when moving from to_apply → applied
- Backup happens automatically before dedup (pipeline.json.bak)
