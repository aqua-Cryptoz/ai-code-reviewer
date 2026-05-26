"""Markdown review report generator."""

from __future__ import annotations

from datetime import datetime


def generate_report(
    filename: str,
    code: str,
    complexity_report,
    security_report,
    style_report,
    llm_review=None,
) -> str:
    """Generate markdown review report.

    Args:
        filename: File reviewed
        code: Source code
        complexity_report: ComplexityAnalyzer result
        security_report: SecurityAnalyzer result
        style_report: StyleAnalyzer result
        llm_review: Optional LLM ReviewResult
    """
    lines = code.splitlines()
    loc = len(lines)

    parts = [
        f"# 🔍 Code Review: `{filename}`",
        f"",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        f"",
        f"---",
        f"",
        f"## 📊 Overview",
        f"",
        f"- **Lines of code:** {loc}",
        f"- **Security score:** {security_report.score}/100",
        f"- **Complexity grade:** {complexity_report.grade}",
        f"- **Style issues:** {style_report.total}",
        f"- **Total issues:** {len(security_report.issues) + style_report.total + len(complexity_report.functions)}",
        f"",
    ]

    # LLM summary
    if llm_review and llm_review.summary:
        parts.extend([
            f"## 🤖 AI Analysis",
            f"",
            f"> {llm_review.summary}",
            f"",
            f"**Rating:** {llm_review.rating}",
            f"",
        ])

    # Security
    parts.extend([
        f"## 🔒 Security Analysis",
        f"",
        f"**Score: {security_report.score}/100** — {security_report.summary}",
        f"",
    ])
    if security_report.issues:
        parts.append("| # | Line | Severity | Category | Issue |")
        parts.append("|---|------|----------|----------|-------|")
        for i, issue in enumerate(security_report.issues, 1):
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(issue.severity, "⚪")
            parts.append(
                f"| {i} | {issue.line} | {icon} {issue.severity} | {issue.category} | {issue.message} |"
            )
    else:
        parts.append("✅ No security issues found.")
    parts.append("")

    # Complexity
    parts.extend([
        f"## 📈 Complexity Analysis",
        f"",
        f"**Grade: {complexity_report.grade}** | "
        f"Total: {complexity_report.total_complexity} | "
        f"Avg: {complexity_report.avg_complexity:.1f}",
        f"",
    ])
    if complexity_report.raw_metrics:
        rm = complexity_report.raw_metrics
        parts.append(
            f"**Metrics:** LOC={rm.get('loc', '?')} | "
            f"SLOC={rm.get('sloc', '?')} | "
            f"Comments={rm.get('comments', '?')} | "
            f"Blank={rm.get('blank', '?')}"
        )
        parts.append("")
    if complexity_report.functions:
        parts.append("| Function | Line | Complexity | Rank |")
        parts.append("|----------|------|------------|------|")
        for f in complexity_report.functions[:15]:
            parts.append(f"| {f['name']} | {f['lineno']} | {f['complexity']} | {f['rank']} |")
    else:
        parts.append("No functions analyzed.")
    parts.append("")

    # Style
    parts.extend([
        f"## 🎨 Style Analysis",
        f"",
        f"**{style_report.total} issue(s) found**",
        f"",
    ])
    if style_report.issues:
        # Group by category
        categories: dict[str, list] = {}
        for issue in style_report.issues:
            categories.setdefault(issue.category, []).append(issue)

        for cat, issues in categories.items():
            cat_name = cat.replace("_", " ").title()
            parts.append(f"### {cat_name} ({len(issues)})")
            parts.append("")
            for issue in issues[:10]:
                parts.append(f"- **Line {issue.line}:** {issue.message}")
            if len(issues) > 10:
                parts.append(f"- *...and {len(issues) - 10} more*")
            parts.append("")
    else:
        parts.append("✅ No style issues found.")
        parts.append("")

    # LLM issues
    if llm_review and llm_review.issues:
        parts.extend([
            f"## 🐛 Issues Detected by AI",
            f"",
        ])
        for issue in llm_review.issues:
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(
                issue.get("severity", ""), "⚪"
            )
            line = issue.get("line", "?")
            cat = issue.get("category", "general")
            msg = issue.get("message", "")
            sev = issue.get("severity", "info")
            parts.append(f"- {icon} **Line {line}** [{sev}] ({cat}): {msg}")
        parts.append("")

    # Suggestions
    all_suggestions = []
    if llm_review and llm_review.suggestions:
        all_suggestions.extend(llm_review.suggestions)

    if all_suggestions:
        parts.extend([
            f"## 💡 Suggestions",
            f"",
        ])
        for s in all_suggestions:
            parts.append(f"- {s}")
        parts.append("")

    parts.extend([
        "---",
        "",
        "*Report generated by AI Code Reviewer — powered by Xiaomi MiMo*",
    ])

    return "\n".join(parts)
