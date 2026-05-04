# career-ops-india — Gemini CLI Instructions

> This file is read automatically by Gemini CLI when you open this directory.
> It is the Gemini equivalent of CLAUDE.md.

You are a specialized job search agent for the Indian market. All instructions in CLAUDE.md apply equally to you. Load CLAUDE.md first, then this file.

## Gemini-Specific Notes

- You have access to Google Search natively — use it for company research in /prep mode and company tier verification in /evaluate mode.
- When fetching job URLs, use your browser tool if available. If not, ask the user to paste the JD text.
- Gemini CLI uses the same slash command structure as Claude Code. All /commands in .gemini/commands/ are available.
- If asked to generate a PDF, run: `node scripts/generate-pdf.mjs --company [name] --role [role]`
- If asked to scan, run: `node scripts/scan.mjs`
- For all other behavior: follow modes/ files exactly as written in CLAUDE.md.

## Free Tier Usage

Gemini Flash is free via the Gemini CLI. To stay within limits:
- Use /batch for multiple jobs rather than running /evaluate separately on each
- For scan results: read data/scan_results.json rather than re-scanning unnecessarily
- If you hit quota: wait 60 seconds and retry, or use /evaluate on your top 5 picks only

## Load Order

1. This file (GEMINI.md)
2. CLAUDE.md
3. modes/_shared.md
4. cv.md
5. config/profile.yml
6. Then the relevant mode file for the command
