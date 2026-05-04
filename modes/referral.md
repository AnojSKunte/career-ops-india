# referral.md — Referral Finder & Outreach Mode
> Trigger: "find someone at [company]", "who do I know at", "referral for [company]", /referral
> Load first: `_shared.md`, `cv.md`

## Why This Matters
In India, referrals bypass HR screening for most Tier 1 startups.
Companies like Razorpay, CRED, Zepto pay ₹50K–₹2L referral bonuses.
Employees are INCENTIVIZED to refer. This is not a favour — it's mutual value.

---

## Step 1 — Find the Right Person to Contact

For a given company, instruct the candidate to:

**LinkedIn search (manual — AI can't log into LinkedIn):**
1. Search: `[Company Name] site:linkedin.com/in`
2. Filter by: 2nd-degree connections first
3. Filter by: Data/Analytics/Product/Engineering teams
4. Target profiles: 2–5 years tenure (invested in company, knows the team)
   Avoid: <6 months tenure (don't know company well), VPs and above (too senior for cold referral ask)

**Best targets:**
- Current Data Analyst / Analytics Engineer at the company → peer-level, knows the job
- Data Engineering or BI team member → knows the hiring manager
- Someone from IIT/NIT (check their education) → shared institution = higher response rate

---

## Step 2 — Personalize the Ask

Before writing the message, extract from their LinkedIn profile:
- What team are they on?
- What projects have they shared publicly?
- Mutual connections?
- Shared college/city?

Use this in the message. Generic outreach gets ignored.

---

## Step 3 — Generate the Referral Message

Customize Template 2 from `contact.md` for this specific person and company.

Key elements:
- Open with 1 line showing you actually looked at their profile
- State your background in 2 lines (IIT + role + specific tools)
- Name the specific job you're applying for
- Make the ask clear but easy to decline
- Under 150 words total

**Anti-patterns to avoid:**
- "I've always admired [Company]'s mission" → generic, sounds like you copied it
- Asking for 30 minutes "to learn more about the role" → they're not a recruiter
- Sending 3 follow-ups → one follow-up maximum, 7 days after first message

---

## Step 4 — Track the Referral

After generating the message:
"Want me to log this outreach in your tracker with status 'referral_pending'?"

If yes, add to pipeline.json:
```json
{
  "company": "...",
  "role": "...",
  "status": "referral_pending",
  "notes": "Reached out to [Name] on LinkedIn on [date]"
}
```

Follow-up reminder: if no response in 7 days, one follow-up, then move on.

---

## Referral Conversion Reality

- Cold apply → interview rate: ~5–10% for competitive roles
- Referral apply → interview rate: ~40–60% for competitive roles
- 1 hour finding the right person and writing a good message = 4–6× better odds

Prioritize referral over cold apply for every Tier 1 company.
