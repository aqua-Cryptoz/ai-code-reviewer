"""Security pattern detection analyzer."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field


@dataclass
class SecurityIssue:
    """A detected security issue."""

    line: int
    col: int
    category: str
    severity: str  # low, medium, high, critical
    message: str
    code_snippet: str = ""


@dataclass
class SecurityReport:
    """Results of security analysis."""

    issues: list[SecurityIssue] = field(default_factory=list)
    score: int = 100  # 0-100, starts perfect

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "high")

    @property
    def summary(self) -> str:
        if not self.issues:
            return "No security issues detected"
        return f"{len(self.issues)} issue(s): {self.critical_count} critical, {self.high_count} high"


DANGEROUS_CALLS = {
    "eval": ("critical", "Use of eval() — risk of arbitrary code execution"),
    "exec": ("critical", "Use of exec() — risk of arbitrary code execution"),
    "compile": ("high", "Use of compile() with dynamic input"),
    "__import__": ("high", "Dynamic import — potential code injection"),
    "getattr": ("low", "Dynamic getattr — review attribute access"),
}

SECRET_PATTERNS = [
    (r'(?i)(password|passwd|secret|token|api_key|apikey)\s*=\s*["\'][^"\']{4,}["\']',
     "hardcoded_secret", "critical", "Hardcoded secret/credential detected"),
    (r'(?i)(aws_access_key_id|aws_secret_access_key)\s*=\s*["\'][A-Z0-9]{16,}["\']',
     "aws_key", "critical", "Hardcoded AWS key detected"),
    (r'["\']sk-[a-zA-Z0-9]{20,}["\']',
     "openai_key", "critical", "Possible OpenAI API key in source"),
    (r'["\']AKIA[A-Z0-9]{16}["\']',
     "aws_access_key", "critical", "AWS Access Key ID in source"),
]

INJECTION_PATTERNS = [
    (r'(?i)(execute|cursor\.execute)\s*\(.*%|\.format\(|f["\']',
     "sql_injection", "high", "Possible SQL injection — use parameterized queries"),
    (r'subprocess\.(call|run|Popen)\s*\(.*shell\s*=\s*True',
     "shell_injection", "high", "shell=True in subprocess — risk of command injection"),
    (r'os\.system\s*\(',
     "os_system", "high", "os.system() — prefer subprocess with shell=False"),
]

INSECURE_NETWORK = [
    (r'http://', "http", "low", "Unencrypted HTTP URL — use HTTPS"),
    (r'verify\s*=\s*False', "ssl_disabled", "high", "SSL verification disabled"),
    (r'check_hostname\s*=\s*False', "hostname_disabled", "high", "Hostname verification disabled"),
]


class SecurityAnalyzer:
    """Detect security issues in Python code."""

    def analyze(self, code: str, source_lines: list[str] | None = None) -> SecurityReport:
        """Run security analysis on source code."""
        report = SecurityReport()

        if source_lines is None:
            source_lines = code.splitlines()

        # AST-based checks
        self._check_ast(code, report, source_lines)

        # Regex-based checks
        self._check_patterns(source_lines, report, SECRET_PATTERNS)
        self._check_patterns(source_lines, report, INJECTION_PATTERNS)
        self._check_patterns(source_lines, report, INSECURE_NETWORK)

        # Deduplicate by (line, category)
        seen = set()
        unique = []
        for issue in report.issues:
            key = (issue.line, issue.category)
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        report.issues = sorted(unique, key=lambda i: i.line)

        # Calculate score
        penalties = {"critical": 25, "high": 15, "medium": 8, "low": 3}
        report.score = max(0, 100 - sum(penalties.get(i.severity, 0) for i in report.issues))

        return report

    def _check_ast(self, code: str, report: SecurityReport, lines: list[str]) -> None:
        """AST-based security checks."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            # Dangerous function calls
            if isinstance(node, ast.Call):
                func_name = self._get_call_name(node)
                if func_name in DANGEROUS_CALLS:
                    severity, msg = DANGEROUS_CALLS[func_name]
                    snippet = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
                    report.issues.append(SecurityIssue(
                        line=node.lineno,
                        col=node.col_offset,
                        category="dangerous_call",
                        severity=severity,
                        message=msg,
                        code_snippet=snippet,
                    ))

            # Assert in non-test code (assertions removed with -O)
            if isinstance(node, ast.Assert):
                report.issues.append(SecurityIssue(
                    line=node.lineno,
                    col=node.col_offset,
                    category="assert_usage",
                    severity="low",
                    message="assert can be disabled with -O flag — don't use for validation",
                ))

            # Bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                report.issues.append(SecurityIssue(
                    line=node.lineno,
                    col=node.col_offset,
                    category="bare_except",
                    severity="low",
                    message="Bare except clause — may hide errors silently",
                ))

    def _check_patterns(
        self,
        lines: list[str],
        report: SecurityReport,
        patterns: list[tuple],
    ) -> None:
        """Regex-based pattern checks."""
        for line_num, line in enumerate(lines, 1):
            for pattern, category, severity, message in patterns:
                if re.search(pattern, line):
                    report.issues.append(SecurityIssue(
                        line=line_num,
                        col=0,
                        category=category,
                        severity=severity,
                        message=message,
                        code_snippet=line.strip(),
                    ))

    @staticmethod
    def _get_call_name(node: ast.Call) -> str:
        """Extract function name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""
