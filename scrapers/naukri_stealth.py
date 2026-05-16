#!/usr/bin/env python3
"""
scrapers/naukri_stealth.py
Naukri scraper using Scrapling — the best open-source anti-bot bypass tool (22k stars).
Uses Camoufox (modified Firefox) to auto-solve Cloudflare Turnstile.

Install once:
    pip install scrapling
    python -m playwright install firefox

Run:
    python scrapers/naukri_stealth.py
"""
import json, random, time, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent

def read_config():
    p = ROOT / "config" / "profile.yml"
    if not p.exists():
        print("config/profile.yml not found. Copy from profile.example.yml")
        sys.exit(1)
    text = p.read_text(encoding="utf-8")
    roles, locations = [], []
    in_roles = in_locs = False
    min_lpa = 10
    for line in text.splitlines():
        if line.strip().startswith("target_roles:"):  in_roles=True;  in_locs=False;  continue
        if line.strip().startswith("locations:"):      in_locs=True;   in_roles=False; continue
        if in_roles and line.startswith("    - "): roles.append(line[6:].strip())
        elif in_roles and not line.startswith("    "): in_roles=False
        if in_locs  and line.startswith("    - "): locations.append(line[6:].strip())
        elif in_locs  and not line.startswith("    "): in_locs=False
        if "min:" in line:
            try: min_lpa = int(line.split(":")[1].strip())
            except: pass
    return {"roles": roles, "locations": locations, "min_lpa": min_lpa}

def build_url(role, page=1, min_lpa=10):
    slug = role.lower().strip().replace(" ", "-").replace("/", "-")
    salary = min_lpa * 100000
    start  = max(0, (page - 1) * 20)
    return f"https://www.naukri.com/{slug}-jobs?experience=0to2&jobAge=14&salary={salary}&start={start}"

def parse_cards(page_obj):
    jobs = []
    cards = []
    for sel in ["article.jobTuple", "div.srp-jobtuple-wrapper", 'li[class*="jobTupleHeader"]']:
        cards = page_obj.css(sel)
        if cards: break
    if not cards:
        print("    No cards found — selectors may need updating or page is blocked.")
        return []
    for card in cards:
        try:
            title_el = (card.css_first("a.title") or card.css_first('a[class*="jobTitle"]')
                        or card.css_first("h2 a"))
            comp_el  = (card.css_first("a.subTitle") or card.css_first('a[class*="companyName"]')
                        or card.css_first('span[class*="companyName"]'))
            if not title_el: continue
            sal_el  = card.css_first('span[class*="salary"]')
            loc_el  = card.css_first('span[class*="loc"]') or card.css_first("span.locWdth")
            exp_el  = card.css_first('span[class*="exp"]')
            desc_el = card.css_first('span[class*="job-desc"]')
            title   = title_el.clean() or ""
            company = comp_el.clean() if comp_el else ""
            url     = title_el.attrib.get("href", "")
            if url and not url.startswith("http"): url = "https://www.naukri.com" + url
            if not title or not url: continue
            jobs.append({
                "source": "naukri", "company": company.strip(), "tier": "unknown",
                "title": title.strip(),
                "location":   loc_el.clean()  if loc_el  else "",
                "salary":     sal_el.clean()   if sal_el  else "Not disclosed",
                "experience": exp_el.clean()   if exp_el  else "",
                "url": url,
                "posted_at": "", "remote": "remote" in (loc_el.clean() if loc_el else "").lower(),
                "snippet": desc_el.clean()[:300] if desc_el else "",
            })
        except: continue
    return jobs

def loc_match(job, locations):
    if not job["location"] or not locations: return True
    loc = job["location"].lower()
    if "remote" in loc: return True
    return any(l.lower() in loc for l in locations)

def main():
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError:
        print("\n❌ Scrapling not installed.")
        print("   pip install scrapling")
        print("   python -m playwright install firefox\n")
        sys.exit(1)

    cfg       = read_config()
    roles     = cfg["roles"]
    locations = cfg["locations"]
    min_lpa   = cfg["min_lpa"]

    all_jobs, seen = [], set()
    print("\n🔍 Naukri (Scrapling + StealthyFetcher — auto-bypasses Cloudflare)")
    print(f"   Roles: {', '.join(roles)}")
    print(f"   Tip: set headless=False below if you want to watch the browser\n")

    for role in roles:
        print(f"  Scraping: {role}")
        found = 0
        for page_num in range(1, 4):
            url = build_url(role, page=page_num, min_lpa=min_lpa)
            print(f"    Page {page_num}...")
            try:
                page = StealthyFetcher.fetch(
                    url,
                    headless=True,
                    humanize=True,
                    solve_cloudflare=True,
                    geoip=True,
                    os_randomize=True,
                    timeout=90000,
                    block_images=True,
                )
                txt = page.get_all_text().lower()
                if "access denied" in txt or "are you a robot" in txt:
                    print("    Blocked. Waiting 60s...")
                    time.sleep(60)
                    continue
                cards = parse_cards(page)
                for j in cards:
                    if not loc_match(j, locations): continue
                    key = f"{j['title'].lower()}|{j['company'].lower()}"
                    if key in seen: continue
                    seen.add(key); all_jobs.append(j); found += 1
                print(f"    {len(cards)} cards → {found} total matches")
                if len(cards) < 15: break
            except Exception as e:
                print(f"    Error: {str(e)[:80]}")
                break
            time.sleep(random.uniform(6, 12))
        print(f"  → {found} jobs for {role!r}")
        time.sleep(random.uniform(10, 18))

    scan = ROOT / "data" / "scan_results.json"
    existing = {"jobs": []}
    if scan.exists():
        try: existing = json.loads(scan.read_text(encoding="utf-8"))
        except: pass
    combined = [j for j in existing.get("jobs", []) if j.get("source") != "naukri"] + all_jobs
    scan.parent.mkdir(exist_ok=True)
    scan.write_text(json.dumps({"scanned_at": datetime.now().isoformat(),
        "total": len(combined), "jobs": combined}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{'─'*50}")
    print(f"✅ Naukri: {len(all_jobs)} jobs | Total in file: {len(combined)}")
    if all_jobs:
        print()
        for i, j in enumerate(all_jobs[:5], 1):
            print(f"  {i}. {j['company']:<22} {j['title']}")
            print(f"     {j['location']} | {j['salary']}")
            print(f"     {j['url']}\n")

if __name__ == "__main__":
    main()
