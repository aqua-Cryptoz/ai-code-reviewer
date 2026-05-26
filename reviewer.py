"""Core code reviewer — orchestrates analysis and LLM review."""

from __future__ import annotations

import ast
from pathlib import Path
from dataclasses import dataclass, field

from analyzers.complexity import ComplexityAnalyzer, ComplexityReport
from analyzers.security import SecurityAnalyzer, SecurityReport
from analyzers.style import StyleAnalyzer, StyleReport
from providers.base import BaseProvider, ReviewResult
from report import generate_report


@dataclass
class ReviewContext:
    """Aggregated review results for a single file."""

    filename: str
    code: str
    complexity: ComplexityReport | None = None
    security: SecurityReport | None = None
    style: StyleReport | None = None
    llm_review: ReviewResult | None = None
    ast_info: dict = field(default_factory=dict)
    error: str | None = None


class CodeReviewer:
    """Main reviewer — reads files, runs analyzers, calls LLM, generates reports."""

    def __init__(self, provider: BaseProvider | None = None):
        self.provider = provider
        self.complexity_analyzer = ComplexityAnalyzer()
        self.security_analyzer = SecurityAnalyzer()
        self.style_analyzer = StyleAnalyzer()

    def review_file(self, filepath: str | Path) -> ReviewContext:
        """Review a single Python file."""
        filepath = Path(filepath)
        ctx = ReviewContext(filename=str(filepath), code="")

        # Read file
        try:
            code = filepath.read_text(encoding="utf-8")
        except Exception as e:
            ctx.error = f"Failed to read {filepath}: {e}"
            return ctx

        ctx.code = code
        return self._analyze_code(ctx)

    def review_code(self, code: str, filename: str = "<string>") -> ReviewContext:
        """Review source code string directly."""
        ctx = ReviewContext(filename=filename, code=code)
        return self._analyze_code(ctx)

    def _analyze_code(self, ctx: ReviewContext) -> ReviewContext:
        """Run all static analyzers."""
        code = ctx.code
        lines = code.splitlines()

        # Extract AST info
        try:
            tree = ast.parse(code)
            ctx.ast_info = self._extract_ast_info(tree)
        except SyntaxError as e:
            ctx.error = f"Syntax error: {e}"
            ctx.ast_info = {}

        # Run analyzers
        ctx.complexity = self.complexity_analyzer.analyze(code)
        ctx.security = self.security_analyzer.analyze(code, lines)
        ctx.style = self.style_analyzer.analyze(code, lines)

        return ctx

    async def review_with_llm(self, ctx: ReviewContext) -> ReviewContext:
        """Enrich review with LLM analysis."""
        if not self.provider or not ctx.code:
            return ctx

        context = {}
        if ctx.complexity:
            context["complexity"] = {
                "functions": ctx.complexity.functions[:20],
                "grade": ctx.complexity.grade,
            }
        if ctx.security:
            context["security"] = {
                "issues": [
                    {"line": i.line, "severity": i.severity, "message": i.message}
                    for i in ctx.security.issues[:30]
                ],
            }

        try:
            ctx.llm_review = await self.provider.review_code(
                ctx.code, ctx.filename, context
            )
        except Exception as e:
            ctx.error = f"LLM review failed: {e}"

        return ctx

    def generate_report(self, ctx: ReviewContext) -> str:
        """Generate markdown report from review context."""
        return generate_report(
            filename=ctx.filename,
            code=ctx.code,
            complexity_report=ctx.complexity or ComplexityReport(),
            security_report=ctx.security or SecurityReport(),
            style_report=ctx.style or StyleReport(),
            llm_review=ctx.llm_review,
        )

    @staticmethod
    def _extract_ast_info(tree: ast.Module) -> dict:
        """Extract high-level AST info for context."""
        info = {"functions": [], "classes": [], "imports": []}

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": len(node.args.args),
                })
            elif isinstance(node, ast.ClassDef):
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                info["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods,
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    info["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [a.name for a in node.names]
                info["imports"].append(f"from {module} import {', '.join(names)}")

        return info

    def find_python_files(self, path: str | Path) -> list[Path]:
        """Find all Python files in a path (file or directory)."""
        path = Path(path)
        if path.is_file():
            return [path] if path.suffix == ".py" else []
        if path.is_dir():
            return sorted(p for p in path.rglob("*.py") if ".venv" not in str(p) and "__pycache__" not in str(p))
        return []
