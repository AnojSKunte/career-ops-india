"""
Career Ops India — Unified CLI Entry Point

Usage:
    python main.py scan                    # Run all tiers
    python main.py scan --safe             # Run Tier 1-3 only (zero ban risk)
    python main.py scan --tier 1           # Run specific tier
    python main.py scan --query "data analyst" --location "Bangalore"
    python main.py results                 # Show top matches
    python main.py results --grade A       # Filter by grade
    python main.py results --source linkedin
    python main.py stats                   # Show pipeline stats
    python main.py export                  # Export to data/scan_results.json
    python main.py import-pipeline         # Import from existing data/pipeline.json
    python main.py dashboard               # Launch TUI dashboard
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Fix Windows console encoding for Unicode/emojis
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    console = Console()
except ImportError:
    import re
    class Panel:
        def __init__(self, text, title=None, **kwargs):
            self.text = text
            self.title = title
        def __str__(self):
            t = f"── {self.title} ──\n" if self.title else ""
            clean = re.sub(r'\[/?[a-zA-Z0-9_\s#=]+\]', '', str(self.text))
            return f"\n{t}{clean}\n"

    class Text:
        def __init__(self, text, style=None):
            self.text = text
        def __str__(self):
            return str(self.text)

    class Table:
        def __init__(self, title=None):
            self.title = title
            self.columns = []
            self.rows = []
        def add_column(self, name, **kwargs):
            self.columns.append(name)
        def add_row(self, *items):
            self.rows.append([str(i) for i in items])
        def __str__(self):
            out = [f"\n=== {self.title} ===" if self.title else ""]
            if self.columns:
                out.append(" | ".join(self.columns))
                out.append("-" * 60)
            for r in self.rows:
                out.append(" | ".join(r))
            return "\n".join(out)

    class Console:
        def print(self, *args, **kwargs):
            clean_args = []
            for a in args:
                if isinstance(a, (Panel, Table, Text)):
                    clean_args.append(str(a))
                else:
                    clean_args.append(re.sub(r'\[/?[a-zA-Z0-9_\s#=]+\]', '', str(a)))
            print(*clean_args)
    console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-25s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("career-ops")


def check_profile():
    """Ensure config/profile.yml exists."""
    if not Path("config/profile.yml").exists():
        if Path("config/profile.example.yml").exists():
            console.print(
                Panel(
                    "[yellow]config/profile.yml not found![/yellow]\n\n"
                    "Copy the example and fill in your details:\n"
                    "  [cyan]cp config/profile.example.yml config/profile.yml[/cyan]\n\n"
                    "Then edit it with your target roles, salary, skills, etc.",
                    title="⚠️ Profile Not Found",
                    border_style="yellow",
                )
            )
        else:
            console.print("[red]Neither profile.yml nor profile.example.yml found![/red]")
        return False
    return True


async def cmd_scan(args):
    """Run job scraping."""
    from engine.aggregator import JobAggregator

    aggregator = JobAggregator()
    queries = [args.query] if args.query else []

    if args.safe:
        console.print(Panel("🛡️ Running SAFE scan (Tiers 1-3 only — zero ban risk)", style="green"))
        stats = await aggregator.run_safe(queries)
    elif args.tier:
        tier_names = {1: "ATS APIs", 2: "Job Aggregator APIs", 3: "RSS Feeds", 4: "JobSpy Multi-Board"}
        console.print(Panel(f"Running Tier {args.tier}: {tier_names.get(args.tier, '?')}", style="cyan"))
        if args.tier == 1:
            stats = await aggregator.run_tier1_ats()
        elif args.tier == 2:
            stats = await aggregator.run_tier2_apis(args.query)
        elif args.tier == 3:
            stats = await aggregator.run_tier3_rss()
        elif args.tier == 4:
            stats = await aggregator.run_tier4_jobspy(queries)
        else:
            console.print("[red]Invalid tier. Use 1-4.[/red]")
            return
    else:
        console.print(Panel("🚀 Running FULL scan (all tiers)", style="bold cyan"))
        stats = await aggregator.run_all(queries)

    # Display results
    console.print()
    if isinstance(stats, dict):
        if "tier_results" in stats:
            table = Table(title="📊 Scan Results Summary")
            table.add_column("Tier", style="cyan")
            table.add_column("Jobs Found", justify="right", style="green")
            table.add_column("New", justify="right", style="bold green")
            table.add_column("Updated", justify="right", style="yellow")
            table.add_column("Status", style="white")

            for r in stats.get("tier_results", []):
                status = "✅" if not r.get("error") else f"❌ {r['error'][:40]}"
                table.add_row(
                    r.get("source", "?"),
                    str(r.get("jobs_found", 0)),
                    str(r.get("jobs_new", 0)),
                    str(r.get("jobs_updated", 0)),
                    status,
                )

            console.print(table)
            console.print(
                f"\n[bold]Total: {stats.get('total_jobs_found', 0)} found, "
                f"{stats.get('total_new', 0)} new[/bold]"
            )
        else:
            # Single tier result
            console.print(f"Jobs found: [green]{stats.get('jobs_found', 0)}[/green]")
            console.print(f"New: [bold green]{stats.get('jobs_new', 0)}[/bold green]")
            console.print(f"Updated: [yellow]{stats.get('jobs_updated', 0)}[/yellow]")

    # Show top matches
    console.print()
    top = aggregator.get_top_matches(min_grade="B", limit=10)
    if top:
        console.print(Panel("🎯 Top 10 Matches (Grade A/B)", style="bold"))
        match_table = Table()
        match_table.add_column("Grade", style="magenta", justify="center")
        match_table.add_column("Score", style="cyan", justify="right")
        match_table.add_column("Company", style="green")
        match_table.add_column("Role", style="blue")
        match_table.add_column("Location", style="white")
        match_table.add_column("Source", style="dim")

        for m in top:
            grade_style = {"A": "bold green", "B": "green"}.get(m.get("grade", ""), "white")
            match_table.add_row(
                Text(m.get("grade", "?"), style=grade_style),
                str(m.get("score", "")),
                m.get("company", ""),
                m.get("title", ""),
                m.get("location", "")[:25] if m.get("location") else "",
                m.get("source", ""),
            )
        console.print(match_table)


def cmd_results(args):
    """Show top job matches from database."""
    from engine.aggregator import JobAggregator

    aggregator = JobAggregator()
    matches = aggregator.get_top_matches(min_grade=args.grade, limit=50)

    if args.source:
        matches = [m for m in matches if m.get("source", "") == args.source]

    if not matches:
        console.print("[yellow]No matches found. Run 'python main.py scan' first.[/yellow]")
        return

    table = Table(title=f"🎯 Top Job Matches (Min Grade: {args.grade})")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Grade", style="magenta", justify="center")
    table.add_column("Score", style="cyan", justify="right")
    table.add_column("Company", style="green")
    table.add_column("Role", style="blue")
    table.add_column("Location", style="white")
    table.add_column("Salary (LPA)", justify="right", style="yellow")
    table.add_column("Source", style="dim")

    for i, m in enumerate(matches, 1):
        salary = ""
        if m.get("salary_min") and m.get("salary_max"):
            salary = f"{m['salary_min']:.0f}-{m['salary_max']:.0f}"
        elif m.get("salary_min"):
            salary = f"{m['salary_min']:.0f}+"

        grade_style = {"A": "bold green", "B": "green", "C": "yellow", "D": "red"}.get(
            m.get("grade", ""), "dim"
        )

        table.add_row(
            str(i),
            Text(m.get("grade", "?"), style=grade_style),
            str(m.get("score", "")),
            m.get("company", ""),
            m.get("title", ""),
            (m.get("location", "") or "")[:25],
            salary,
            m.get("source", ""),
        )

    console.print(table)
    console.print(f"\n[dim]Showing {len(matches)} results. Use --grade A to filter further.[/dim]")


def cmd_stats(args):
    """Show pipeline statistics."""
    from engine.aggregator import JobAggregator

    aggregator = JobAggregator()
    summary = aggregator.get_summary()

    console.print(Panel("📊 Career Ops Pipeline Statistics", style="bold cyan"))

    # Job stats
    job_stats = summary.get("job_stats", {})
    if job_stats.get("by_source"):
        table = Table(title="Jobs by Source")
        table.add_column("Source", style="cyan")
        table.add_column("Count", justify="right", style="green")
        for source, count in sorted(job_stats["by_source"].items(), key=lambda x: -x[1]):
            table.add_row(source, str(count))
        console.print(table)

    if job_stats.get("by_grade"):
        table = Table(title="Jobs by Grade")
        table.add_column("Grade", style="magenta")
        table.add_column("Count", justify="right", style="green")
        for grade in ["A", "B", "C", "D", "F"]:
            count = job_stats["by_grade"].get(grade, 0)
            if count:
                table.add_row(grade, str(count))
        console.print(table)

    active = job_stats.get("active_status", {})
    console.print(f"Active jobs: [green]{active.get('active', 0)}[/green]")
    console.print(f"Inactive jobs: [dim]{active.get('inactive', 0)}[/dim]")

    # Pipeline stats
    pipeline = summary.get("pipeline_stats", {})
    if pipeline.get("by_status"):
        console.print()
        table = Table(title="Application Pipeline")
        table.add_column("Status", style="cyan")
        table.add_column("Count", justify="right", style="green")
        for status, count in pipeline["by_status"].items():
            table.add_row(status, str(count))
        console.print(table)
        console.print(f"Interview rate: [bold]{pipeline.get('interview_rate', 0):.1f}%[/bold]")


def cmd_export(args):
    """Export jobs to data/scan_results.json for backward compatibility."""
    from db.job_store import JobStore

    store = JobStore()
    jobs = store.get_active_jobs()

    output = []
    for job in jobs:
        output.append({
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "salary": job.salary_raw,
            "url": job.job_url,
            "source": job.source,
            "grade": job.grade,
            "score": job.fit_score,
            "description": (job.description_snippet or "")[:200],
        })

    Path("data").mkdir(exist_ok=True)
    with open("data/scan_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    console.print(f"[green]✅ Exported {len(output)} jobs to data/scan_results.json[/green]")


def cmd_import_pipeline(args):
    """Import from existing data/pipeline.json."""
    from db.job_store import JobStore

    path = "data/pipeline.json"
    if not Path(path).exists():
        console.print(f"[red]{path} not found.[/red]")
        return

    store = JobStore()
    store.import_pipeline_json(path)
    console.print(f"[green]✅ Imported pipeline data from {path}[/green]")


def cmd_dashboard(args):
    """Launch the TUI dashboard."""
    import subprocess
    console.print("[cyan]Launching TUI Dashboard...[/cyan]")
    subprocess.run([sys.executable, "tui/dashboard.py"], check=False)


async def async_main():
    parser = argparse.ArgumentParser(
        description="Career Ops India — AI-powered job search engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py scan                     Run all scraping tiers
  python main.py scan --safe              Zero ban risk (Tiers 1-3 only)
  python main.py scan --tier 1            ATS APIs only
  python main.py scan --query "data analyst"
  python main.py results --grade A        Show Grade A matches
  python main.py stats                    Pipeline statistics
  python main.py export                   Export to scan_results.json
        """,
    )
    subparsers = parser.add_subparsers(dest="command")

    # scan
    scan_p = subparsers.add_parser("scan", help="Run job scraping tiers")
    scan_p.add_argument("--safe", action="store_true", help="Run Tier 1-3 only (zero ban risk)")
    scan_p.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run specific tier")
    scan_p.add_argument("--query", type=str, help="Search query (e.g. 'data analyst')")
    scan_p.add_argument("--location", type=str, default="India", help="Location filter")

    # results
    res_p = subparsers.add_parser("results", help="Show top job matches")
    res_p.add_argument("--grade", type=str, default="C", help="Minimum grade (A/B/C/D/F)")
    res_p.add_argument("--source", type=str, help="Filter by source (linkedin, greenhouse, etc.)")

    # stats
    subparsers.add_parser("stats", help="Show pipeline statistics")

    # export
    subparsers.add_parser("export", help="Export to data/scan_results.json")

    # import-pipeline
    subparsers.add_parser("import-pipeline", help="Import from data/pipeline.json")

    # dashboard
    subparsers.add_parser("dashboard", help="Launch TUI dashboard")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Check profile exists (except for import/export)
    if args.command in ("scan", "results", "stats"):
        check_profile()

    # Route commands
    if args.command == "scan":
        await cmd_scan(args)
    elif args.command == "results":
        cmd_results(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "import-pipeline":
        cmd_import_pipeline(args)
    elif args.command == "dashboard":
        cmd_dashboard(args)


def main():
    console.print(
        Panel(
            "[bold cyan]Career Ops India[/bold cyan] 🇮🇳\n"
            "[dim]AI-powered job search engine — scan, evaluate, apply[/dim]",
            style="cyan",
        )
    )
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted by user.[/red]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()
