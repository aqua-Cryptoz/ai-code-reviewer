"""Style and convention analyzer."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

MAX_LINE_LENGTH = 100
MAX_FUNCTION_LINES = 50
MAX_FUNCTION_ARGS = 5
MAX_NESTING_DEPTH = 4


@dataclass
class StyleIssue:
    """A style issue found in code."""

    line: int
    category: str
    severity: str  # info, low, medium
    message: str


@dataclass
class StyleReport:
    """Results of style analysis."""

    issues: list[StyleIssue] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.issues)


class StyleAnalyzer:
    """Detect style and convention issues in Python code."""

    def analyze(self, code: str, source_lines: list[str] | None = None) -> StyleReport:
        """Run style analysis."""
        report = StyleReport()

        if source_lines is None:
            source_lines = code.splitlines()

        self._check_lines(source_lines, report)
        self._check_ast(code, report, source_lines)

        report.issues.sort(key=lambda i: i.line)
        return report

    def _check_lines(self, lines: list[str], report: StyleReport) -> None:
        """Line-level style checks."""
        prev_blank_count = 0

        for line_num, line in enumerate(lines, 1):
            # Long lines
            if len(line) > MAX_LINE_LENGTH:
                report.issues.append(StyleIssue(
                    line=line_num,
                    category="line_length",
                    severity="info",
                    message=f"Line too long ({len(line)} > {MAX_LINE_LENGTH} chars)",
                ))

            # Trailing whitespace
            if line != line.rstrip():
                report.issues.append(StyleIssue(
                    line=line_num,
                    category="trailing_whitespace",
                    severity="info",
                    message="Trailing whitespace",
                ))

            # Consecutive blank lines
            if line.strip() == "":
                prev_blank_count += 1
                if prev_blank_count > 2:
                    report.issues.append(StyleIssue(
                        line=line_num,
                        category="blank_lines",
                        severity="info",
                        message="Too many consecutive blank lines",
                    ))
            else:
                prev_blank_count = 0

            # Tab characters
            if "\t" in line:
                report.issues.append(StyleIssue(
                    line=line_num,
                    category="tab_usage",
                    severity="info",
                    message="Tab character — prefer spaces",
                ))

    def _check_ast(self, code: str, report: StyleReport, lines: list[str]) -> None:
        """AST-based style checks."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            # Function checks
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._check_function(node, report, lines)

            # Class checks
            if isinstance(node, ast.ClassDef):
                self._check_class(node, report)

            # Import checks
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "*":
                        report.issues.append(StyleIssue(
                            line=node.lineno,
                            category="wildcard_import",
                            severity="medium",
                            message="Wildcard import (from x import *) — prefer explicit imports",
                        ))

            # String concatenation in loops (perf-related style)
            if isinstance(node, ast.For):
                self._check_string_concat_in_loop(node, report)

    def _check_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, report: StyleReport, lines: list[str]
    ) -> None:
        """Check function conventions."""
        name = node.name

        # Naming convention
        if name.startswith("_") and not name.startswith("__"):
            pass  # private — ok
        elif name.startswith("__") and name.endswith("__"):
            pass  # dunder — ok
        elif not name.islower() and "_" not in name and name[0] != "_":
            # Not snake_case (allow PascalCase only for class methods)
            if not name[0].isupper():
                report.issues.append(StyleIssue(
                    line=node.lineno,
                    category="naming",
                    severity="low",
                    message=f"Function '{name}' — use snake_case",
                ))

        # Missing docstring
        if not (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, (ast.Constant, ast.Str))
        ):
            # Skip dunder and private
            if not name.startswith("_"):
                report.issues.append(StyleIssue(
                    line=node.lineno,
                    category="docstring",
                    severity="low",
                    message=f"Function '{name}' missing docstring",
                ))

        # Too many arguments
        args = node.args
        arg_count = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
        if args.vararg:
            arg_count += 1
        if args.kwarg:
            arg_count += 1
        # Subtract 'self'/'cls'
        if arg_count > 0 and args.args and args.args[0].arg in ("self", "cls"):
            arg_count -= 1

        if arg_count > MAX_FUNCTION_ARGS:
            report.issues.append(StyleIssue(
                line=node.lineno,
                category="too_many_args",
                severity="medium",
                message=f"Function '{name}' has {arg_count} args (max {MAX_FUNCTION_ARGS})",
            ))

        # Function length
        if hasattr(node, "end_lineno") and node.end_lineno:
            length = node.end_lineno - node.lineno + 1
            if length > MAX_FUNCTION_LINES:
                report.issues.append(StyleIssue(
                    line=node.lineno,
                    category="function_length",
                    severity="medium",
                    message=f"Function '{name}' is {length} lines (max {MAX_FUNCTION_LINES})",
                ))

    def _check_class(self, node: ast.ClassDef, report: StyleReport) -> None:
        """Check class conventions."""
        # Missing docstring
        if not (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, (ast.Constant, ast.Str))
        ):
            report.issues.append(StyleIssue(
                line=node.lineno,
                category="docstring",
                severity="low",
                message=f"Class '{node.name}' missing docstring",
            ))

    def _check_string_concat_in_loop(self, node: ast.For, report: StyleReport) -> None:
        """Check for string concatenation in loops (O(n²) pattern)."""
        for child in ast.walk(node):
            if isinstance(child, ast.AugAssign) and isinstance(child.op, ast.Add):
                if isinstance(child.target, ast.Name):
                    report.issues.append(StyleIssue(
                        line=child.lineno,
                        category="performance",
                        severity="medium",
                        message="String concatenation in loop — use ''.join() or list append",
                    ))
