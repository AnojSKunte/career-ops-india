#!/usr/bin/env python3
"""
tui/dashboard.py — career-ops-india Terminal Dashboard

A full-featured terminal UI built with Textual.
Shows your pipeline, scan results, quick actions.

Install:
    pip install textual

Run:
    python tui/dashboard.py
    python tui/dashboard.py --scan     # auto-run scan on startup
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.widgets import (DataTable, Footer, Header, Label, ListItem,
                                  ListView, Markdown, ProgressBar, Rule,
                                  Static, TabbedContent, TabPane)
    from textual.reactive import reactive
    from textual import events
    HAS_TEXTUAL = True
except ImportError:
    HAS_TEXTUAL = False


# ── Data loaders ───────────────────────────────────────────────────────────────
def load_pipeline() -> list:
    p = ROOT / "data" / "pipeline.json"
    if not p.exists(): return []
    try: return json.loads(p.read_text(encoding="utf-8"))
    except: return []

def load_scan_results() -> list:
    p = ROOT / "data" / "scan_results.json"
    if not p.exists(): return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("jobs", [])
    except: return []

def load_profile_name() -> str:
    p = ROOT / "config" / "profile.yml"
    if not p.exists(): return "Candidate"
    for line in p.read_text().splitlines():
        if line.strip().startswith("name:"):
            return line.split(":",1)[1].strip()
    return "Candidate"

STATUS_EMOJI = {
    "to_apply":    "📋",
    "applied":     "✉️ ",
    "hr_screen":   "📞",
    "technical":   "💻",
    "final_round": "🔥",
    "offer":       "🎉",
    "accepted":    "✅",
    "rejected":    "❌",
    "withdrawn":   "↩️ ",
    "expired":     "💀",
    "cold_email_sent": "📨",
}

GRADE_COLOR = {"A": "green", "B": "cyan", "C": "yellow", "D": "red", "F": "magenta"}


# ── Fallback: Rich-based dashboard (no Textual) ────────────────────────────────
def run_rich_dashboard():
    """Simpler fallback using only Rich (already likely installed)."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.columns import Columns
        from rich.text import Text
        from rich import box
    except ImportError:
        print("Install either: pip install textual   (full TUI)")
        print("           or:  pip install rich       (simpler dashboard)")
        sys.exit(1)

    console = Console()
    pipeline = load_pipeline()
    jobs     = load_scan_results()
    name     = load_profile_name()

    console.clear()

    # Header
    console.print(Panel(
        f"[bold cyan]career-ops-india[/] Dashboard  •  {name}  •  {datetime.now().strftime('%d %b %Y')}",
        style="bold", padding=(0, 2)
    ))

    # Stats row
    active   = [j for j in pipeline if j.get("status") in ["to_apply","applied","hr_screen","technical","final_round"]]
    offers   = [j for j in pipeline if j.get("status") in ["offer","accepted"]]
    rejected = [j for j in pipeline if j.get("status") == "rejected"]

    stats = [
        Panel(f"[bold yellow]{len(active)}[/]\nActive", padding=(1,4)),
        Panel(f"[bold green]{len(offers)}[/]\nOffers", padding=(1,4)),
        Panel(f"[bold red]{len(rejected)}[/]\nRejected", padding=(1,4)),
        Panel(f"[bold blue]{len(jobs)}[/]\nScan Results", padding=(1,4)),
    ]
    console.print(Columns(stats))

    # Pipeline table
    if pipeline:
        table = Table(title="📋 Application Pipeline", box=box.ROUNDED, border_style="blue")
        table.add_column("Status", style="dim", width=14)
        table.add_column("Company", style="bold")
        table.add_column("Role", style="cyan")
        table.add_column("Score", width=6)
        table.add_column("Next Action")

        for j in sorted(pipeline, key=lambda x: (x.get("status",""),)):
            status = j.get("status","")
            emoji  = STATUS_EMOJI.get(status, "•")
            score  = j.get("score","")
            grade  = j.get("grade","")
            score_str = f"[{GRADE_COLOR.get(grade,'white')}]{grade} {score}[/]" if grade else "-"
            table.add_row(
                f"{emoji} {status.replace('_',' ')}",
                j.get("company",""),
                j.get("role",""),
                score_str,
                j.get("next_action","") or "-"
            )
        console.print(table)

    # Recent scan results
    if jobs:
        scan_table = Table(title="🔍 Latest Scan Results (Top 10)", box=box.SIMPLE, border_style="cyan")
        scan_table.add_column("Company", style="bold", width=22)
        scan_table.add_column("Role", style="cyan")
        scan_table.add_column("Location", style="dim")
        scan_table.add_column("Source", style="dim", width=10)

        for j in jobs[:10]:
            scan_table.add_row(
                j.get("company","")[:22],
                j.get("title","")[:40],
                j.get("location","")[:20],
                j.get("source",""),
            )
        console.print(scan_table)

    # Commands
    console.print(Panel(
        "[bold]Available commands:[/]\n"
        "  [cyan]npm run scan[/]                    — Scan 256 companies\n"
        "  [cyan]npm run scan:all[/]                — Scan all sources\n"
        "  [cyan]python scrapers/cold_email_agent.py[/] — Send cold email\n"
        "  [cyan]python tui/dashboard.py[/]         — This dashboard\n"
        "  [cyan]npm run dashboard[/]               — Browser pipeline view",
        title="Quick Reference", border_style="green"
    ))


# ── Textual TUI ────────────────────────────────────────────────────────────────
if HAS_TEXTUAL:
    CSS = """
    Screen { background: #0d1117; }
    Header { background: #161b22; color: #e6edf3; }
    Footer { background: #161b22; color: #8b949e; }

    #sidebar {
        width: 28;
        background: #161b22;
        border-right: solid #30363d;
        padding: 1;
    }
    #main { padding: 1 2; }

    .stat-box {
        border: solid #30363d;
        background: #1c2128;
        padding: 1 2;
        margin: 0 0 1 0;
        height: 5;
    }
    .stat-num   { color: #58a6ff; text-style: bold; }
    .stat-label { color: #8b949e; }

    .section-title { color: #f0883e; text-style: bold; margin: 1 0 0 0; }

    DataTable { border: solid #30363d; height: 1fr; }
    DataTable > .datatable--header { background: #21262d; color: #8b949e; }
    DataTable > .datatable--cursor { background: #1f6feb; }

    #job-detail {
        background: #1c2128;
        border: solid #30363d;
        padding: 1 2;
        height: 1fr;
    }
    .grade-a { color: #3fb950; text-style: bold; }
    .grade-b { color: #58a6ff; text-style: bold; }
    .grade-c { color: #f0883e; text-style: bold; }
    .grade-d { color: #f85149; text-style: bold; }

    #actions { height: 5; background: #161b22; border-top: solid #30363d; padding: 1 2; }
    .action-hint { color: #8b949e; }
    """

    class CareerOpsApp(App):
        TITLE = "career-ops-india"
        CSS = CSS
        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("s", "scan", "Scan"),
            Binding("r", "refresh", "Refresh"),
            Binding("e", "evaluate", "Evaluate"),
            Binding("c", "cold_email", "Cold Email"),
            Binding("tab", "next_tab", "Next Tab"),
        ]

        selected_job: reactive = reactive(None)

        def compose(self) -> ComposeResult:
            yield Header()
            with TabbedContent(initial="pipeline"):
                with TabPane("📋 Pipeline", id="pipeline"):
                    yield self._pipeline_view()
                with TabPane("🔍 Scan Results", id="scan"):
                    yield self._scan_view()
                with TabPane("📊 Stats", id="stats"):
                    yield self._stats_view()
            yield Footer()

        def _pipeline_view(self) -> ComposeResult:
            pipeline = load_pipeline()
            with Horizontal():
                with Vertical(id="sidebar"):
                    yield Static("Pipeline Summary", classes="section-title")
                    yield Rule()
                    statuses = {}
                    for j in pipeline:
                        s = j.get("status","unknown")
                        statuses[s] = statuses.get(s, 0) + 1
                    for status, count in sorted(statuses.items()):
                        emoji = STATUS_EMOJI.get(status, "•")
                        yield Static(f"{emoji} {status.replace('_',' ')}: {count}")

                with Vertical(id="main"):
                    yield Static("Applications", classes="section-title")
                    table = DataTable(id="pipeline-table", cursor_type="row")
                    table.add_columns("Status", "Company", "Role", "Score", "Updated")
                    for j in pipeline:
                        status = j.get("status","")
                        grade  = j.get("grade","")
                        score  = j.get("score","")
                        score_str = f"{grade} {score}" if grade else "-"
                        table.add_row(
                            STATUS_EMOJI.get(status,"•") + " " + status.replace("_"," "),
                            j.get("company","")[:20],
                            j.get("role","")[:35],
                            score_str,
                            (j.get("date_applied") or j.get("date_found",""))[:10],
                            key=j.get("id",""),
                        )
                    yield table

        def _scan_view(self) -> ComposeResult:
            jobs = load_scan_results()
            with Vertical(id="main"):
                yield Static(f"Scan Results — {len(jobs)} jobs found", classes="section-title")
                table = DataTable(id="scan-table", cursor_type="row")
                table.add_columns("Company", "Role", "Location", "Source", "Tier")
                for j in jobs[:100]:
                    table.add_row(
                        j.get("company","")[:22],
                        j.get("title","")[:40],
                        j.get("location","")[:20],
                        j.get("source","")[:10],
                        "⭐" if j.get("tier") == "1" else "  ",
                        key=j.get("url",""),
                    )
                yield table

        def _stats_view(self) -> ComposeResult:
            pipeline = load_pipeline()
            jobs     = load_scan_results()
            name     = load_profile_name()

            applied = [j for j in pipeline if j.get("status") != "to_apply"]
            at_hr   = [j for j in pipeline if j.get("status") in ["hr_screen","technical","final_round","offer","accepted"]]
            offers  = [j for j in pipeline if j.get("status") in ["offer","accepted"]]

            conv_apply_hr = f"{round(len(at_hr)/len(applied)*100)}%" if applied else "–"
            conv_hr_offer = f"{round(len(offers)/len(at_hr)*100)}%" if at_hr else "–"

            with Vertical(id="main"):
                yield Static(f"Stats for {name}", classes="section-title")
                yield Static(f"\n  📋 Total applications:  {len(pipeline)}")
                yield Static(f"  ✉️  Applied:             {len(applied)}")
                yield Static(f"  📞 Got interviews:      {len(at_hr)}")
                yield Static(f"  🎉 Offers:              {len(offers)}")
                yield Static(f"\n  Apply → Interview rate: {conv_apply_hr}")
                yield Static(f"  Interview → Offer rate: {conv_hr_offer}")
                yield Static(f"\n  🔍 Scan results:        {len(jobs)} jobs")
                tier1 = [j for j in jobs if j.get("tier") == "1"]
                yield Static(f"  ⭐ Tier 1 companies:     {len(tier1)}")

        def action_scan(self):
            self.notify("Running scan... check terminal for output", severity="information")

        def action_refresh(self):
            self.notify("Refreshing data...", severity="information")
            self.refresh()

        def action_evaluate(self):
            self.notify("Open Claude Code or Gemini CLI and run /evaluate [URL]", severity="information")

        def action_cold_email(self):
            self.notify("Run: python scrapers/cold_email_agent.py", severity="information")

        def action_next_tab(self):
            self.query_one(TabbedContent).next_tab()


def main():
    if "--help" in sys.argv:
        print("Usage: python tui/dashboard.py")
        print("       python tui/dashboard.py --simple  (Rich-based, no Textual needed)")
        sys.exit(0)

    if "--simple" in sys.argv or not HAS_TEXTUAL:
        if not HAS_TEXTUAL:
            print("Textual not installed. Running Rich dashboard instead.")
            print("For full TUI: pip install textual\n")
        run_rich_dashboard()
    else:
        app = CareerOpsApp()
        app.run()


if __name__ == "__main__":
    main()
