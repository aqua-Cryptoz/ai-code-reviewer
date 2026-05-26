"""Cyclomatic complexity analyzer using radon."""

from __future__ import annotations

from dataclasses import dataclass, field

try:
    from radon.complexity import cc_visit, cc_rank
    from radon.raw import analyze as raw_analyze
    HAS_RADON = True
except ImportError:
    HAS_RADON = False


@dataclass
class ComplexityReport:
    """Results of complexity analysis."""

    functions: list[dict] = field(default_factory=list)
    total_complexity: int = 0
    avg_complexity: float = 0.0
    raw_metrics: dict = field(default_factory=dict)
    grade: str = "N/A"


class ComplexityAnalyzer:
    """Analyze cyclomatic complexity of Python code."""

    def analyze(self, code: str) -> ComplexityReport:
        """Run complexity analysis on source code."""
        report = ComplexityReport()

        if not HAS_RADON:
            return report

        try:
            blocks = cc_visit(code)
        except Exception:
            return report

        funcs = []
        total = 0
        for block in blocks:
            rank = cc_rank(block.complexity)
            funcs.append({
                "name": block.name,
                "lineno": block.lineno,
                "endline": block.endline,
                "complexity": block.complexity,
                "rank": rank,
                "is_class": getattr(block, "is_class", False),
            })
            total += block.complexity

        funcs.sort(key=lambda f: f["complexity"], reverse=True)
        report.functions = funcs
        report.total_complexity = total
        report.avg_complexity = total / len(funcs) if funcs else 0

        # Raw metrics
        try:
            raw = raw_analyze(code)
            report.raw_metrics = {
                "loc": raw.loc,
                "lloc": raw.lloc,
                "sloc": raw.sloc,
                "comments": raw.comments,
                "multi": raw.multi,
                "blank": raw.blank,
            }
        except Exception:
            pass

        # Overall grade
        avg = report.avg_complexity
        if avg <= 5:
            report.grade = "A"
        elif avg <= 10:
            report.grade = "B"
        elif avg <= 20:
            report.grade = "C"
        elif avg <= 30:
            report.grade = "D"
        else:
            report.grade = "F"

        return report
