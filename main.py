#!/usr/bin/env python3
"""AI Code Reviewer — CLI entry point.

Usage:
    python main.py <file_or_dir>     Review file(s)
    python main.py --demo            Run demo with sample code
    python main.py --demo --demo-only  Run demo without waiting for key press
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import os
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich import box

from reviewer import CodeReviewer
from providers.mimo_provider import MiMoProvider

console = Console()

# ── Sample code for demo mode ───────────────────────────────────────────

DEMO_CODE = '''\
"""Sample API handler — demo file for code review."""

import os
import json
from flask import Flask, request

app = Flask(__name__)
password = "super_secret_123"

def get_user_data( user_id, include_meta, format_type, cache, verbose, extra ):
    """Fetch user data from the database."""
    
    query = "SELECT * FROM users WHERE id = %s" % user_id
    cursor.execute(query)
    result = cursor.fetchone()
    
    data = eval(result["raw_data"])
    meta = getattr(result, "metadata", {})
    
    if verbose:
        print("Got data for user", user_id)
    
    output = ""
    for item in data:
        output += str(item)
    
    return output

class userManager:
    def process(self, x):
        try:
            val = int(x)
            return val
        except:
            pass
        return None

    def run_command(self, cmd):
        import subprocess
        return subprocess.call(cmd, shell=True)

def connect_api():
    import requests
    r = requests.get("http://api.example.com/data", verify=False)
    return r.json()
'''


def print_banner():
    """Print startup banner."""
    banner = Text()
    banner.append("🔍 AI Code Reviewer", style="bold cyan")
    banner.append("  — powered by ", style="dim")
    banner.append("Xiaomi MiMo", style="bold magenta")
    console.print()
    console.print(Panel(banner, border_style="cyan", box=box.DOUBLE))
    console.print()


def print_file_header(filename: str, index: int, total: int):
    """Print file review header."""
    header = f"📄 Reviewing [{index}/{total}]: {filename}"
    console.print(Panel(header, style="bold green", box=box.HEAVY))


def render_complexity_table(complexity_report) -> None:
    """Render complexity results as Rich table."""
    if not complexity_report:
        return

    table = Table(
        title="📈 Complexity Analysis",
        box=box.ROUNDED,
        title_style="bold cyan",
    )
    table.add_column("Function", style="bold")
    table.add_column("Line", justify="right")
    table.add_column("Complexity", justify="center")
    table.add_column("Rank", justify="center")

    rank_colors = {"A": "green", "B": "green", "C": "yellow", "D": "red", "E": "red", "F": "bold red"}

    for f in complexity_report.functions[:15]:
        color = rank_colors.get(f["rank"], "white")
        table.add_row(
            f["name"],
            str(f["lineno"]),
            str(f["complexity"]),
            f"[{color}]{f['rank']}[/{color}]",
        )

    if not complexity_report.functions:
        table.add_row("(no functions found)", "", "", "")

    console.print(table)

    # Summary line
    grade_color = rank_colors.get(complexity_report.grade, "white")
    console.print(
        f"  Grade: [{grade_color}]{complexity_report.grade}[/{grade_color}] | "
        f"Total: {complexity_report.total_complexity} | "
        f"Avg: {complexity_report.avg_complexity:.1f}"
    )
    if complexity_report.raw_metrics:
        rm = complexity_report.raw_metrics
        console.print(
            f"  LOC: {rm.get('loc', '?')} | SLOC: {rm.get('sloc', '?')} | "
            f"Comments: {rm.get('comments', '?')} | Blank: {rm.get('blank', '?')}"
        )
    console.print()


def render_security_table(security_report) -> None:
    """Render security results as Rich table."""
    if not security_report:
        return

    score = security_report.score
    score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
    console.print(
        f"🔒 [bold]Security Analysis[/bold] — Score: [{score_color}]{score}/100[/{score_color}]"
    )

    if not security_report.issues:
        console.print("  ✅ [green]No security issues detected[/green]")
        console.print()
        return

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Line", justify="right")
    table.add_column("Severity", justify="center")
    table.add_column("Category")
    table.add_column("Issue")

    severity_colors = {
        "critical": "bold red",
        "high": "red",
        "medium": "yellow",
        "low": "blue",
    }
    severity_icons = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🔵",
    }

    for i, issue in enumerate(security_report.issues[:20], 1):
        color = severity_colors.get(issue.severity, "white")
        icon = severity_icons.get(issue.severity, "⚪")
        table.add_row(
            str(i),
            str(issue.line),
            f"{icon} [{color}]{issue.severity}[/{color}]",
            issue.category,
            issue.message,
        )

    console.print(table)
    if len(security_report.issues) > 20:
        console.print(f"  ... and {len(security_report.issues) - 20} more issues")
    console.print()


def render_style_table(style_report) -> None:
    """Render style results as Rich table."""
    if not style_report:
        return

    console.print(f"🎨 [bold]Style Analysis[/bold] — {style_report.total} issue(s)")

    if not style_report.issues:
        console.print("  ✅ [green]No style issues found[/green]")
        console.print()
        return

    # Group by category
    categories: dict[str, list] = {}
    for issue in style_report.issues:
        categories.setdefault(issue.category, []).append(issue)

    table = Table(box=box.ROUNDED)
    table.add_column("Category", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Sample Issues")

    category_icons = {
        "docstring": "📝",
        "naming": "🏷️",
        "line_length": "📏",
        "trailing_whitespace": "␣",
        "blank_lines": "📄",
        "tab_usage": "⇥",
        "too_many_args": "📦",
        "function_length": "📐",
        "wildcard_import": "⚠️",
        "performance": "⚡",
    }

    for cat, issues in sorted(categories.items(), key=lambda x: -len(x[1])):
        icon = category_icons.get(cat, "•")
        cat_display = cat.replace("_", " ").title()
        samples = "; ".join(i.message for i in issues[:3])
        if len(issues) > 3:
            samples += f" (+{len(issues) - 3} more)"
        table.add_row(f"{icon} {cat_display}", str(len(issues)), samples)

    console.print(table)
    console.print()


def render_llm_review(llm_review) -> None:
    """Render LLM review results."""
    if not llm_review:
        return

    console.print("🤖 [bold cyan]AI Analysis (MiMo)[/bold cyan]")

    if llm_review.summary:
        console.print(Panel(llm_review.summary, border_style="cyan", title="Summary"))

    if llm_review.rating:
        rating_colors = {
            "excellent": "bold green",
            "good": "green",
            "needs_work": "yellow",
            "poor": "red",
        }
        color = rating_colors.get(llm_review.rating.lower(), "white")
        console.print(f"  Rating: [{color}]{llm_review.rating}[/{color}]")

    if llm_review.issues:
        console.print()
        severity_icons = {
            "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵",
        }
        for issue in llm_review.issues:
            icon = severity_icons.get(issue.get("severity", ""), "⚪")
            line = issue.get("line", "?")
            msg = issue.get("message", "")
            sev = issue.get("severity", "info")
            console.print(f"  {icon} Line {line} [{sev}]: {msg}")

    if llm_review.suggestions:
        console.print()
        console.print("  💡 [bold]Suggestions:[/bold]")
        for s in llm_review.suggestions:
            console.print(f"    • {s}")

    console.print()


async def run_demo():
    """Run demo with sample code."""
    print_banner()

    console.print("[bold yellow]📋 Demo Mode[/bold yellow] — analyzing sample Python file\n")

    # Show the sample code
    console.print(Panel(
        Syntax(DEMO_CODE, "python", theme="monokai", line_numbers=True),
        title="Sample Code",
        border_style="dim",
    ))

    console.print()

    reviewer = CodeReviewer(provider=None)
    ctx = reviewer.review_code(DEMO_CODE, filename="sample_api_handler.py")

    # Simulate LLM review for demo
    from providers.base import ReviewResult
    ctx.llm_review = ReviewResult(
        summary=(
            "This code has several critical security vulnerabilities including SQL injection, "
            "use of eval(), and hardcoded credentials. The string concatenation in a loop "
            "creates a performance bottleneck, and bare except clauses mask errors. "
            "Naming conventions need fixing. Code needs significant rework before production use."
        ),
        issues=[
            {"line": 11, "category": "security", "severity": "critical", "message": "SQL injection via string formatting — use parameterized queries"},
            {"line": 15, "category": "security", "severity": "critical", "message": "eval() on untrusted data — arbitrary code execution risk"},
            {"line": 22, "category": "performance", "severity": "medium", "message": "String concatenation in loop — O(n²), use ''.join()"},
            {"line": 30, "category": "error_handling", "severity": "high", "message": "Bare except clause swallows all exceptions silently"},
            {"line": 28, "category": "style", "severity": "low", "message": "Class 'userManager' should be PascalCase: 'UserManager'"},
        ],
        suggestions=[
            "Replace `eval()` with `json.loads()` for safe deserialization",
            "Use parameterized queries: `cursor.execute('SELECT ... WHERE id = %s', (user_id,))`",
            "Use `join()`: `output = ''.join(str(item) for item in data)`",
            "Catch specific exceptions instead of bare except",
            "Rename class to PascalCase and add docstring",
            "Remove hardcoded password — use environment variables",
            "Set `verify=True` for HTTPS requests",
        ],
        rating="needs_work",
    )

    print_file_header(ctx.filename, 1, 1)
    render_complexity_table(ctx.complexity)
    render_security_table(ctx.security)
    render_style_table(ctx.style)
    render_llm_review(ctx.llm_review)

    # Generate and show report path
    report_content = reviewer.generate_report(ctx)
    report_path = Path("demo_review_report.md")
    report_path.write_text(report_content)
    console.print(f"📝 Report saved to: [bold]{report_path.absolute()}[/bold]")
    console.print()


async def run_review(paths: list[str], provider=None):
    """Run actual code review."""
    print_banner()

    reviewer = CodeReviewer(provider=provider)

    # Collect files
    all_files: list[Path] = []
    for p in paths:
        found = reviewer.find_python_files(p)
        if not found:
            console.print(f"[yellow]⚠ No Python files found at: {p}[/yellow]")
        all_files.extend(found)

    if not all_files:
        console.print("[red]No Python files to review.[/red]")
        sys.exit(1)

    console.print(f"Found [bold]{len(all_files)}[/bold] Python file(s) to review\n")

    for i, filepath in enumerate(all_files, 1):
        print_file_header(str(filepath), i, len(all_files))

        ctx = reviewer.review_file(filepath)

        if ctx.error:
            console.print(f"[red]Error: {ctx.error}[/red]")
            continue

        # LLM review if provider available
        if provider:
            console.print("  🤖 Calling MiMo API for deep analysis...", style="dim")
            ctx = await reviewer.review_with_llm(ctx)

        render_complexity_table(ctx.complexity)
        render_security_table(ctx.security)
        render_style_table(ctx.style)
        render_llm_review(ctx.llm_review)

        # Save report
        report_content = reviewer.generate_report(ctx)
        safe_name = Path(filepath).stem
        report_path = Path(f"review_{safe_name}.md")
        report_path.write_text(report_content)
        console.print(f"  📝 Report: [dim]{report_path}[/dim]")
        console.print()

    console.print("[bold green]✅ Review complete![/bold green]")


def main():
    parser = argparse.ArgumentParser(
        description="AI Code Reviewer — powered by Xiaomi MiMo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --demo                  Run demo mode
  python main.py app.py                  Review single file
  python main.py src/                    Review directory
  python main.py app.py --provider mimo  Use MiMo API
        """,
    )
    parser.add_argument("paths", nargs="*", help="File or directory to review")
    parser.add_argument("--demo", action="store_true", help="Run demo with sample code")
    parser.add_argument("--provider", choices=["mimo"], default=None, help="LLM provider")
    parser.add_argument("--api-key", default=None, help="API key (or set MIMO_API_KEY env var)")
    parser.add_argument("--model", default=None, help="Model name override")
    parser.add_argument("--base-url", default=None, help="API base URL override")

    args = parser.parse_args()

    # Build provider if requested
    provider = None
    if args.provider == "mimo":
        api_key = args.api_key or os.environ.get("MIMO_API_KEY", "")
        if not api_key:
            console.print("[red]Error: MiMo API key required. Set MIMO_API_KEY or use --api-key[/red]")
            sys.exit(1)
        kwargs = {"api_key": api_key}
        if args.model:
            kwargs["model"] = args.model
        if args.base_url:
            kwargs["base_url"] = args.base_url
        provider = MiMoProvider(**kwargs)

    if args.demo:
        asyncio.run(run_demo())
    elif args.paths:
        asyncio.run(run_review(args.paths, provider=provider))
    else:
        parser.print_help()
        console.print("\n[dim]Tip: Run with --demo to see a sample review[/dim]")


if __name__ == "__main__":
    main()
