#!/usr/bin/env python3
"""
scrapers/cold_email_agent.py — Cold email drafting, approval, and sending

Flow:
1. Load job from pipeline or by URL
2. Find the right contact (email_finder.py)
3. Draft a personalized cold email using LLM
4. Show draft to user — user approves, edits, or cancels
5. Send via SMTP (Gmail)
6. Log to data/pipeline.json with status 'cold_email_sent'

Setup for Gmail:
    1. Go to myaccount.google.com → Security → 2-Step Verification → App passwords
    2. Create app password for "Mail"
    3. Set env vars:
       export EMAIL_FROM=your@gmail.com
       export EMAIL_PASSWORD=your-app-password

Run:
    python scrapers/cold_email_agent.py                   # interactive
    python scrapers/cold_email_agent.py --job-url <url>   # from URL
    python scrapers/cold_email_agent.py --pipeline-id 5   # from tracker
"""
import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ── LLM email drafter ──────────────────────────────────────────────────────────
def get_llm_config():
    gemini_key = os.environ.get("GEMINI_API_KEY")
    claude_key  = os.environ.get("ANTHROPIC_API_KEY")
    openai_key  = os.environ.get("OPENAI_API_KEY")
    if gemini_key:
        return {"api_key": gemini_key, "model": "google_genai/gemini-2.0-flash"}
    elif claude_key:
        return {"api_key": claude_key, "model": "anthropic/claude-haiku-4-5-20251001"}
    elif openai_key:
        return {"api_key": openai_key, "model": "openai/gpt-4o-mini"}
    return None


def draft_cold_email(cv_text: str, job: dict, contact: dict, candidate_name: str) -> dict:
    """
    Use LLM to draft a personalized cold email.
    Returns: {"subject": str, "body": str}
    """
    llm_cfg = get_llm_config()
    if not llm_cfg:
        # Fallback template if no LLM available
        return draft_template_email(job, contact, candidate_name)

    prompt = f"""You are writing a cold email for a job application in the Indian market.

CANDIDATE:
{cv_text[:800]}

JOB:
Company: {job.get('company')}
Role: {job.get('title')}
Location: {job.get('location')}
Key requirements: {', '.join((job.get('requirements') or job.get('tech_stack') or [])[:5])}

RECIPIENT:
Name: {contact.get('name')}
Title: {contact.get('title')}

RULES — strictly follow these:
- Under 120 words total (cold emails must be short — this is non-negotiable)
- Subject line: specific, not generic. Mention role + one differentiator.
- Opening: reference something specific about {contact.get('name')}'s work or company (not generic praise)
- Body: who you are in 1 sentence (IIT + current role + key tool), 1 sentence on why this company specifically, clear ask
- No "I hope this email finds you well". No "I am passionate about". No bullet points.
- Closing: simple ask for 15 minutes, not "at your earliest convenience"
- Sign off with just the name

Return ONLY a JSON object:
{{"subject": "email subject", "body": "full email body"}}"""

    try:
        if "gemini" in llm_cfg.get("model", ""):
            import google.generativeai as genai
            genai.configure(api_key=llm_cfg["api_key"])
            m = genai.GenerativeModel(llm_cfg["model"].split("/")[-1])
            response = m.generate_content(prompt)
            text = response.text
        elif "anthropic" in llm_cfg.get("model", ""):
            import anthropic
            client = anthropic.Anthropic(api_key=llm_cfg["api_key"])
            msg = client.messages.create(
                model=llm_cfg["model"].split("/")[-1],
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            text = msg.content[0].text
        else:
            return draft_template_email(job, contact, candidate_name)

        # Parse JSON response
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())

    except Exception as e:
        print(f"   LLM draft failed ({e}), using template")
        return draft_template_email(job, contact, candidate_name)


def draft_template_email(job: dict, contact: dict, candidate_name: str) -> dict:
    """Fallback template — still personalized, no LLM needed."""
    company   = job.get("company", "your company")
    role      = job.get("title", "the data analyst role")
    c_name    = contact.get("name", "").split()[0] if contact.get("name") else "Hi"
    first_name = candidate_name.split()[0]

    subject = f"{role} — {candidate_name}, IIT Hyderabad"
    body = f"""Hi {c_name},

I came across the {role} opening at {company} and wanted to reach out directly.

I'm {candidate_name} — IIT Hyderabad grad, currently at Recykal as a Strategy Analyst building Python ETL pipelines and Metabase dashboards. I've been following {company}'s work closely and the problems your data team is solving are exactly what I want to be working on.

Would you have 15 minutes to connect? Happy to share my work or CV if useful.

{first_name}"""

    return {"subject": subject, "body": body}


# ── Email sender ───────────────────────────────────────────────────────────────
def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email via SMTP (Gmail). Returns True if sent."""
    from_email = os.environ.get("EMAIL_FROM")
    password   = os.environ.get("EMAIL_PASSWORD")

    if not from_email or not password:
        print("\n⚠️  Email credentials not set.")
        print("   Set these environment variables:")
        print("   export EMAIL_FROM=your@gmail.com")
        print("   export EMAIL_PASSWORD=your-gmail-app-password")
        print("   (Get app password: myaccount.google.com → Security → App passwords)\n")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_email
    msg["To"]      = to_email
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_email, password)
            server.sendmail(from_email, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"   Send failed: {e}")
        return False


# ── Pipeline tracker ───────────────────────────────────────────────────────────
def log_email_to_pipeline(job: dict, contact: dict, subject: str):
    """Add cold email to pipeline.json for tracking."""
    pipeline_path = ROOT / "data" / "pipeline.json"
    pipeline = []
    if pipeline_path.exists():
        try:
            pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Find existing entry or create new
    existing = next((j for j in pipeline
                     if j.get("company","").lower() == job.get("company","").lower()
                     and j.get("role","").lower() == job.get("title","").lower()), None)

    entry = existing or {
        "id": str(len(pipeline) + 1),
        "company": job.get("company", ""),
        "role": job.get("title", ""),
        "status": "cold_email_sent",
        "source": job.get("source", "manual"),
        "url": job.get("url", ""),
        "salary_listed": job.get("salary", ""),
        "location": job.get("location", ""),
        "date_found": datetime.now().strftime("%Y-%m-%d"),
        "date_applied": None,
    }

    entry["cold_email"] = {
        "sent_to": contact.get("name"),
        "sent_to_title": contact.get("title"),
        "sent_to_email": contact.get("email"),
        "subject": subject,
        "sent_at": datetime.now().isoformat(),
        "follow_up_due": __import__("datetime").date.today().replace(
            day=min(__import__("datetime").date.today().day + 7, 28)
        ).isoformat(),
        "replied": False,
    }
    entry["status"] = "cold_email_sent"
    entry["next_action"] = f"Follow up with {contact.get('name')} by {entry['cold_email']['follow_up_due']}"

    if not existing:
        pipeline.append(entry)

    pipeline_path.write_text(
        json.dumps(pipeline, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"   ✅ Logged to pipeline.json (follow-up due: {entry['cold_email']['follow_up_due']})")


# ── CV reader ──────────────────────────────────────────────────────────────────
def read_cv() -> str:
    cv_path = ROOT / "cv.md"
    if cv_path.exists():
        return cv_path.read_text(encoding="utf-8")
    return ""


def read_config_name() -> str:
    profile_path = ROOT / "config" / "profile.yml"
    if profile_path.exists():
        for line in profile_path.read_text().splitlines():
            if line.strip().startswith("name:"):
                return line.split(":", 1)[1].strip()
    return "Candidate"


# ── Main interactive flow ──────────────────────────────────────────────────────
def run_interactive():
    print("\n✉️  Cold Email Agent — career-ops-india")
    print("─"*50)

    # Get job info
    print("\nEnter the job you want to cold email about:")
    company   = input("  Company name: ").strip()
    role      = input("  Role title: ").strip()
    website   = input("  Company website (e.g. https://razorpay.com): ").strip()
    job_url   = input("  Job posting URL (optional): ").strip()

    job = {
        "company": company,
        "title": role,
        "url": job_url or website,
        "location": "",
        "salary": "",
        "requirements": [],
        "tech_stack": [],
        "source": "manual",
    }

    # If job URL provided, scrape it for better context
    if job_url:
        print(f"\n🔍 Scraping job details from {job_url}...")
        try:
            from scrapers.smart_job_scraper import scrape_job_url
            scraped = scrape_job_url(job_url)
            if scraped.get("title"):
                job.update(scraped)
                print(f"   Got: {scraped.get('title')} at {scraped.get('company')}")
        except Exception as e:
            print(f"   Scraping skipped: {e}")

    # Find contacts
    from scrapers.email_finder import find_contacts
    contact_data = find_contacts(company, website)

    if not contact_data["contacts"]:
        print("\n⚠️  No contacts found automatically.")
        print("   Enter contact details manually:")
        name  = input("  Contact name: ").strip()
        title = input("  Their title: ").strip()
        email = input("  Their email: ").strip()
        contact = {"name": name, "title": title, "email": email, "source": "manual"}
    else:
        print("\n📋 Found contacts (sorted by relevance):")
        for i, c in enumerate(contact_data["contacts"][:3], 1):
            print(f"  {i}. {c.get('name')} — {c.get('title')}")
            print(f"     Email: {c.get('email') or '(pattern-guessed)'} [{c.get('email_confidence','')}]")

        choice = input(f"\nUse which contact? (1-{min(3,len(contact_data['contacts']))} or enter email manually): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(contact_data["contacts"]):
            contact = contact_data["contacts"][int(choice)-1]
        else:
            email = choice if "@" in choice else input("Enter email: ").strip()
            contact = {"name": input("Contact name: ").strip(), "title": "", "email": email, "source": "manual"}

    # Get/confirm email
    if not contact.get("email") or "@" not in (contact.get("email") or ""):
        contact["email"] = input(f"\n  Email for {contact.get('name')}: ").strip()

    # Draft email
    print(f"\n📝 Drafting cold email to {contact.get('name')}...")
    cv_text   = read_cv()
    cand_name = read_config_name()
    draft     = draft_cold_email(cv_text, job, contact, cand_name)

    # Show draft
    print("\n" + "═"*60)
    print(f"TO:      {contact.get('name')} <{contact.get('email')}>")
    print(f"SUBJECT: {draft['subject']}")
    print("─"*60)
    print(draft["body"])
    print("═"*60)

    word_count = len(draft["body"].split())
    print(f"\n📊 Word count: {word_count} {'✅ Good' if word_count <= 130 else '⚠️ Too long (aim for <120 words)'}")

    # User approval
    print("\nOptions:")
    print("  [s] Send this email")
    print("  [e] Edit subject/body first (opens in terminal)")
    print("  [c] Copy to clipboard and send manually")
    print("  [x] Cancel")

    action = input("\nChoice (s/e/c/x): ").strip().lower()

    if action == "e":
        print("\nEdit subject (press Enter to keep current):")
        new_subject = input(f"  Subject [{draft['subject']}]: ").strip()
        if new_subject:
            draft["subject"] = new_subject
        print("\nEdit body (type new body, end with '---' on a new line):")
        lines = []
        while True:
            line = input()
            if line == "---":
                break
            lines.append(line)
        if lines:
            draft["body"] = "\n".join(lines)
        action = "s"  # proceed to send

    if action == "s":
        print(f"\n📤 Sending to {contact.get('email')}...")
        sent = send_email(contact["email"], draft["subject"], draft["body"])
        if sent:
            print(f"   ✅ Email sent to {contact.get('name')} <{contact.get('email')}>")
            log_email_to_pipeline(job, contact, draft["subject"])
            print(f"\n🗓️  Follow-up reminder: 7 days from now")
            print(f"   If no reply in 7 days, send one follow-up. Then move on.\n")
        else:
            print("   Email not sent. Check your credentials above.")

    elif action == "c":
        print("\n📋 Copy this email manually:")
        print(f"\nTo: {contact.get('email')}")
        print(f"Subject: {draft['subject']}\n")
        print(draft["body"])
        confirm = input("\nMark as sent in tracker? (y/n): ").strip().lower()
        if confirm == "y":
            log_email_to_pipeline(job, contact, draft["subject"])

    else:
        print("\nCancelled. Email not sent.")


if __name__ == "__main__":
    run_interactive()
