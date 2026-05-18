#!/usr/bin/env python3
"""
scrapers/smart_job_scraper.py — Universal job scraper using ScrapeGraphAI

Instead of brittle CSS selectors that break when sites redesign,
this uses an LLM to read any job page and extract structured data.
Works with ANY job board — Naukri, LinkedIn, company pages, etc.

Works with: Gemini (free), Claude, OpenAI, Ollama (local/free)
Provider is auto-detected from environment variables.

Install:
    pip install scrapegraphai
    playwright install

Run:
    python scrapers/smart_job_scraper.py <URL>
    python scrapers/smart_job_scraper.py https://boards.greenhouse.io/razorpay/jobs/123
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

JOB_EXTRACTION_PROMPT = """
Extract job listing information from this page and return a JSON object with these exact fields:
{
  "title": "exact job title",
  "company": "company name",
  "location": "city/cities or Remote",
  "salary": "salary/CTC if mentioned, else null",
  "experience_required": "years required if mentioned, else null",
  "employment_type": "full-time/part-time/contract/internship",
  "remote": true or false,
  "apply_url": "direct application URL if different from current page, else null",
  "posted_date": "date if visible, else null",
  "description": "full job description text",
  "requirements": ["list of required skills/qualifications"],
  "responsibilities": ["list of key responsibilities"],
  "company_description": "brief company description if on page",
  "tech_stack": ["specific tools/technologies mentioned"]
}
If a field is not found, use null. Return ONLY the JSON object, no other text.
"""

EMAIL_EXTRACTION_PROMPT = """
Extract contact information for the data/analytics/product team or hiring contacts from this page.
Look for: team pages, about pages, leadership pages, hiring pages.
Return a JSON object:
{
  "contacts": [
    {
      "name": "full name",
      "title": "job title",
      "email": "email if visible",
      "linkedin": "linkedin URL if visible",
      "relevance": "hiring_manager/data_team_lead/recruiter/founder/other",
      "confidence": "high/medium/low"
    }
  ],
  "company_email_pattern": "pattern like firstname@company.com if detectable",
  "careers_email": "careers@company.com or similar if found"
}
Return ONLY the JSON object. If no contacts found, return {"contacts": [], "company_email_pattern": null, "careers_email": null}
"""


def get_llm_config() -> dict:
    """
    Auto-detect available LLM from environment variables.
    Priority: Gemini (free) → Claude → OpenAI → fail with instructions.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    claude_key  = os.environ.get("ANTHROPIC_API_KEY")
    openai_key  = os.environ.get("OPENAI_API_KEY")

    if gemini_key:
        return {
            "llm": {
                "api_key": gemini_key,
                "model": "google_genai/gemini-2.0-flash",
            },
            "verbose": False,
            "headless": True,
        }
    elif claude_key:
        return {
            "llm": {
                "api_key": claude_key,
                "model": "anthropic/claude-haiku-4-5-20251001",
            },
            "verbose": False,
            "headless": True,
        }
    elif openai_key:
        return {
            "llm": {
                "api_key": openai_key,
                "model": "openai/gpt-4o-mini",
            },
            "verbose": False,
            "headless": True,
        }
    else:
        # Try Ollama (local, completely free)
        return {
            "llm": {
                "model": "ollama/llama3.2",
                "base_url": "http://localhost:11434",
            },
            "verbose": False,
            "headless": True,
        }


def scrape_job_url(url: str) -> dict:
    """
    Scrape any job URL and return structured job data.
    Uses ScrapeGraphAI — no CSS selectors, works on any site.
    """
    try:
        from scrapegraphai.graphs import SmartScraperGraph
    except ImportError:
        print("❌ ScrapeGraphAI not installed.")
        print("   pip install scrapegraphai && playwright install")
        sys.exit(1)

    config = get_llm_config()
    provider = list(config["llm"].values())[1] if "model" in config["llm"] else "unknown"
    print(f"   Using LLM: {config['llm'].get('model', 'unknown')}")

    graph = SmartScraperGraph(
        prompt=JOB_EXTRACTION_PROMPT,
        source=url,
        config=config,
    )

    try:
        result = graph.run()
        if isinstance(result, str):
            result = json.loads(result)

        # Normalize and add metadata
        result["url"] = url
        result["source"] = "smart_scraper"
        result["scraped_at"] = __import__("datetime").datetime.now().isoformat()
        return result

    except Exception as e:
        print(f"   ⚠️  Extraction error: {e}")
        return {"url": url, "title": "", "company": "", "error": str(e)}


def scrape_company_contacts(company_url: str) -> dict:
    """
    Scrape company website for hiring manager / data team contacts.
    Tries multiple pages: /team, /about, /careers, /people
    """
    try:
        from scrapegraphai.graphs import SmartScraperGraph
    except ImportError:
        return {"contacts": []}

    config = get_llm_config()

    # Try different company pages that might have team info
    candidate_urls = [
        company_url,
        company_url.rstrip("/") + "/team",
        company_url.rstrip("/") + "/about",
        company_url.rstrip("/") + "/people",
        company_url.rstrip("/") + "/about-us",
        company_url.rstrip("/") + "/leadership",
    ]

    all_contacts = []
    email_pattern = None
    careers_email = None

    for url in candidate_urls[:3]:  # Try max 3 pages
        try:
            graph = SmartScraperGraph(
                prompt=EMAIL_EXTRACTION_PROMPT,
                source=url,
                config=config,
            )
            result = graph.run()
            if isinstance(result, str):
                result = json.loads(result)

            contacts = result.get("contacts", [])
            if contacts:
                all_contacts.extend(contacts)
            if result.get("company_email_pattern"):
                email_pattern = result["company_email_pattern"]
            if result.get("careers_email"):
                careers_email = result["careers_email"]

            if len(all_contacts) >= 3:
                break

        except Exception:
            continue

    # Deduplicate contacts by name
    seen_names = set()
    unique_contacts = []
    for c in all_contacts:
        name = (c.get("name") or "").lower().strip()
        if name and name not in seen_names:
            seen_names.add(name)
            unique_contacts.append(c)

    return {
        "contacts": unique_contacts,
        "company_email_pattern": email_pattern,
        "careers_email": careers_email,
    }


def save_to_scan_results(job: dict):
    """Merge scraped job into data/scan_results.json"""
    scan_path = ROOT / "data" / "scan_results.json"
    existing = {"jobs": []}
    if scan_path.exists():
        try:
            existing = json.loads(scan_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Check for duplicate by URL
    if any(j.get("url") == job.get("url") for j in existing["jobs"]):
        print(f"   Already in scan results: {job.get('url')}")
        return

    existing["jobs"].insert(0, job)
    existing["total"] = len(existing["jobs"])
    scan_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"   Added to data/scan_results.json")


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrapers/smart_job_scraper.py <URL>")
        print("Example: python scrapers/smart_job_scraper.py https://boards.greenhouse.io/razorpay/jobs/123")
        sys.exit(1)

    url = sys.argv[1]
    print(f"\n🔍 Smart Job Scraper (ScrapeGraphAI)\n   URL: {url}\n")

    job = scrape_job_url(url)

    if job.get("title"):
        print(f"\n✅ Extracted:")
        print(f"   Title:    {job.get('title')}")
        print(f"   Company:  {job.get('company')}")
        print(f"   Location: {job.get('location')}")
        print(f"   Salary:   {job.get('salary') or 'Not disclosed'}")
        print(f"   Stack:    {', '.join(job.get('tech_stack') or [])}")

        save_to_scan_results(job)
        print(f"\n💾 Full data saved. Run /evaluate {url} in Claude Code or Gemini CLI.\n")
    else:
        print(f"\n⚠️  Could not extract job data. Error: {job.get('error')}\n")
