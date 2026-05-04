# Contributing to career-ops-india

Thanks for wanting to help. Here's what's most useful.

---

## Adding a company to the scan list

This is the highest-value contribution. Every company added benefits everyone using the tool.

1. Find the company's careers page
2. Check the URL to identify their ATS:
   - `boards.greenhouse.io/SLUG` → greenhouse
   - `jobs.lever.co/SLUG` → lever
   - `jobs.ashbyhq.com/SLUG` → ashby
   - `[company].wd3.myworkdayjobs.com` → workday (not yet supported)
3. Test the slug: open `https://boards-api.greenhouse.io/v1/boards/SLUG/jobs` in your browser. If you see JSON with jobs, the slug is correct.
4. Add to `portals/india.yml`:
```yaml
  - name: Company Name
    slug: their-slug
    tier: "1"      # 1 = major funded startup, 2 = growth stage, 3 = IT services
    domain: fintech
```
5. Open a PR. Title format: `portal: add [Company Name]`

---

## Fixing a broken slug

ATS slugs change when companies rebrand or switch providers.

If `npm run scan` shows errors for a company:
1. Visit their careers page and find the new URL
2. Update the slug in `portals/india.yml`
3. PR title: `portal: fix [Company Name] slug`

---

## Improving a mode file

Mode files in `modes/` are plain English instructions the AI follows.
If you find a mode gives bad output (wrong evaluation, missing Indian context, etc.):
1. Edit the relevant `.md` file
2. Describe what was wrong and what you changed in the PR

---

## Reporting bugs

Use the Bug Report issue template. Include:
- Which command failed (`/evaluate`, `npm run scan`, etc.)
- Your Node version (`node --version`)
- The error output

---

## What not to do

- Don't commit `cv.md`, `config/profile.yml`, or anything in `data/`, `reports/`, `output/`
- Don't add personal information to portals or modes
- Don't add companies you haven't verified (check the slug actually returns jobs)
