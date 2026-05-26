"""Base LLM provider abstraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ReviewResult:
    """Result from LLM code review."""

    summary: str = ""
    issues: list[dict] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    rating: str = "N/A"


class BaseProvider(ABC):
    """Abstract base for LLM providers."""

    def __init__(self, api_key: str = "", model: str = "", base_url: str = ""):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @abstractmethod
    async def review_code(self, code: str, filename: str, context: dict) -> ReviewResult:
        """Send code to LLM for review.

        Args:
            code: Python source code
            filename: File being reviewed
            context: Extra context from static analyzers
        """
        ...

    def _build_prompt(self, code: str, filename: str, context: dict) -> str:
        """Build review prompt for LLM."""
        complexity_info = ""
        if "complexity" in context:
            funcs = context["complexity"].get("functions", [])
            if funcs:
                complexity_info = "\n".join(
                    f"  - {f['name']}: complexity {f['complexity']}"
                    for f in funcs
                )

        security_info = ""
        if "security" in context:
            issues = context["security"].get("issues", [])
            if issues:
                security_info = "\n".join(
                    f"  - Line {i['line']}: {i['message']}" for i in issues
                )

        complexity_section = f"Complexity metrics:\n{complexity_info}" if complexity_info else "No complexity data."
        security_section = f"Security flags:\n{security_info}" if security_info else "No security flags."

        return f"""You are a senior Python code reviewer. Analyze the following code and provide:
1. A brief summary (2-3 sentences)
2. List of issues found (bug, security, performance, style) with line numbers and severity
3. Improvement suggestions
4. Overall rating: excellent / good / needs_work / poor

Filename: {filename}

Static analysis context:
{complexity_section}
{security_section}

```python
{code}
```

Respond in this JSON format:
{{
  "summary": "...",
  "issues": [{{"line": N, "category": "...", "severity": "low|medium|high|critical", "message": "..."}}],
  "suggestions": ["..."],
  "rating": "..."
}}
"""
