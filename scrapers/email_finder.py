#!/usr/bin/env python3
"""
scrapers/email_finder.py — Find the right person to cold email

Strategy (in order of reliability):
1. ScrapeGraphAI on company /team and /about pages
2. Hunter.io API (25 free searches/month — set HUNTER_API_KEY)
3. Pattern-based guessing + verification

The goal is to find: hiring manager > data team lead > recruiter
NOT: generic info@company.com or careers@company.com (those get ignored)

Run:
    python scrapers/email_finder.py <company_name> <company_website>
    python scrapers/email_finder.py "Razorpay" "https://razorpay.com"
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent


# ── Email pattern generator ────────────────────────────────────────────────────
COMMON_EMAIL_PATTERNS = [
    "{first}@{domain}",
    "{first}.{last}@{domain}",
    "{first}{last}@{domain}",
    "{first}_{last}@{domain}",
    "{f}{last}@{domain}",
    "{first}.{l}@{domain}",
]

def generate_email_guesses(name: str, domain: str) -> list[str]:
    """Generate likely email addresses for a person at a company."""
    parts = name.lower().strip().split()
    if len(parts) < 2:
        return [f"{parts[0]}@{domain}"] if parts else []

    first = parts[0]
    last  = parts[-1]
    f     = first[0]
    l     = last[0]

    emails = []
    for pattern in COMMON_EMAIL_PATTERNS:
        email = pattern.format(
            first=first, last=last,
            f=f, l=l, domain=domain
        )
        # Remove special characters except . and @
        email = re.sub(r"[^a-z0-9.@_-]", "", email)
        if email not in emails:
            emails.append(email)

    return emails


def get_domain(website: str) -> str:
    """Extract root domain from URL. https://razorpay.com → razorpay.com"""
    try:
        parsed = urlparse(website)
        domain = parsed.netloc or parsed.path
        # Remove www.
        return re.sub(r"^www\.", "", domain).strip("/")
    except Exception:
        return website


# ── Hunter.io integration ──────────────────────────────────────────────────────
def search_hunter(company_domain: str, role_keywords: list[str]) -> list[dict]:
    """
    Use Hunter.io API to find emails at a company.
    Free tier: 25 searches/month.
    Set HUNTER_API_KEY environment variable.
    """
    api_key = os.environ.get("HUNTER_API_KEY")
    if not api_key:
        return []

    try:
        import urllib.request
        url = f"https://api.hunter.io/v2/domain-search?domain={company_domain}&api_key={api_key}&limit=10"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())

        emails = data.get("data", {}).get("emails", [])
        contacts = []

        # Prioritize people in data/analytics/product roles
        priority_keywords = ["data", "analytics", "analyst", "product", "engineering",
                             "head of data", "chief", "director", "lead", "manager"]

        for email_obj in emails:
            title = (email_obj.get("position") or "").lower()
            is_relevant = any(kw in title for kw in priority_keywords)
            relevance = "data_team_lead" if is_relevant else "other"
            if email_obj.get("position"):
                contacts.append({
                    "name": f"{email_obj.get('first_name','')} {email_obj.get('last_name','')}".strip(),
                    "title": email_obj.get("position", ""),
                    "email": email_obj.get("value", ""),
                    "source": "hunter.io",
                    "confidence": "high" if email_obj.get("confidence", 0) > 70 else "medium",
                    "relevance": relevance,
                })

        # Sort: data-relevant contacts first
        contacts.sort(key=lambda c: 0 if c["relevance"] == "data_team_lead" else 1)
        return contacts[:5]

    except Exception as e:
        return []


# ── ScrapeGraphAI contact finder ───────────────────────────────────────────────
def scrape_for_contacts(website: str) -> list[dict]:
    """Use ScrapeGraphAI to find team contacts from company pages."""
    try:
        from scrapers.smart_job_scraper import scrape_company_contacts
        result = scrape_company_contacts(website)
        return result.get("contacts", [])
    except Exception:
        return []


# ── LinkedIn public profile search (no login) ──────────────────────────────────
def build_linkedin_search_url(company: str, role: str = "data") -> str:
    """Build a Google search URL to find LinkedIn profiles."""
    query = f'site:linkedin.com/in "{company}" "{role}" analyst OR engineer'
    return f"https://www.google.com/search?q={query.replace(' ', '+')}"


# ── Contact prioritization ─────────────────────────────────────────────────────
PRIORITY_TITLES = [
    ("hiring_manager",    ["head of data", "vp data", "director of analytics", "head of analytics",
                           "chief data officer", "cdo", "data lead", "analytics lead"]),
    ("data_team_lead",    ["data analyst lead", "senior data analyst", "analytics manager",
                           "data engineering manager", "analytics engineer", "data scientist"]),
    ("recruiter",         ["recruiter", "talent acquisition", "hr", "hiring", "people ops"]),
    ("founder",           ["founder", "ceo", "cto", "co-founder"]),
    ("other",             []),
]

def score_contact(contact: dict) -> int:
    """Score a contact by how likely they are the right person to email."""
    title = (contact.get("title") or "").lower()
    for priority, (relevance, keywords) in enumerate(PRIORITY_TITLES):
        if any(kw in title for kw in keywords):
            return priority
    return len(PRIORITY_TITLES)


# ── Main finder ────────────────────────────────────────────────────────────────
def find_contacts(company: str, website: str, role_context: str = "data analyst") -> dict:
    """
    Find the best person(s) to cold email at a company for a data/analytics role.
    Returns ranked list of contacts with email guesses.
    """
    domain = get_domain(website)
    print(f"\n🔍 Finding contacts at {company} ({domain})...")

    all_contacts = []

    # Step 1: Hunter.io (most reliable if API key available)
    print("   → Checking Hunter.io...", end="", flush=True)
    hunter_contacts = search_hunter(domain, [])
    if hunter_contacts:
        all_contacts.extend(hunter_contacts)
        print(f" {len(hunter_contacts)} found")
    else:
        print(" no API key or no results")

    # Step 2: ScrapeGraphAI on company pages
    print("   → Scraping company pages...", end="", flush=True)
    scraped_contacts = scrape_for_contacts(website)
    if scraped_contacts:
        all_contacts.extend(scraped_contacts)
        print(f" {len(scraped_contacts)} found")
    else:
        print(" none found")

    # Step 3: Deduplicate by name + generate email guesses
    seen = set()
    unique = []
    for c in all_contacts:
        name = (c.get("name") or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())

        # Add email guesses if no email found
        if not c.get("email"):
            guesses = generate_email_guesses(name, domain)
            c["email_guesses"] = guesses[:3]
            c["email"] = guesses[0] if guesses else None
            c["email_confidence"] = "low (pattern-guessed)"
        else:
            c["email_guesses"] = []
            c["email_confidence"] = c.get("confidence", "medium")

        unique.append(c)

    # Sort by relevance
    unique.sort(key=score_contact)

    # Step 4: Google search URL as fallback for manual lookup
    linkedin_search = build_linkedin_search_url(company, "data analytics")

    result = {
        "company": company,
        "domain": domain,
        "contacts": unique[:5],   # Top 5 only
        "recommended": unique[0] if unique else None,
        "linkedin_search_url": linkedin_search,
        "manual_fallback": f"Search: {company} data team lead site:linkedin.com",
    }

    # Summary
    print(f"\n   Found {len(unique)} unique contacts")
    if unique:
        best = unique[0]
        print(f"   ⭐ Best contact: {best.get('name')} ({best.get('title')})")
        print(f"      Email: {best.get('email') or 'unknown'} [{best.get('email_confidence','')}]")

    return result


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scrapers/email_finder.py <company_name> <website>")
        print('Example: python scrapers/email_finder.py "Razorpay" "https://razorpay.com"')
        sys.exit(1)

    company = sys.argv[1]
    website = sys.argv[2]

    result = find_contacts(company, website)

    print("\n" + "─"*50)
    print(f"Contact report for {company}")
    print("─"*50)

    for i, c in enumerate(result["contacts"], 1):
        print(f"\n{i}. {c.get('name')} — {c.get('title')}")
        print(f"   Email:  {c.get('email') or 'Not found'}")
        if c.get("email_guesses"):
            print(f"   Guesses: {', '.join(c['email_guesses'][:2])}")
        print(f"   Source: {c.get('source','scraped')} | Confidence: {c.get('email_confidence','?')}")

    if not result["contacts"]:
        print("\nNo contacts found automatically.")
        print(f"Manual search: {result['linkedin_search_url']}")

    print("\n💡 Next: python scrapers/cold_email_agent.py to draft and send an email.\n")
