"""Xiaomi MiMo LLM provider integration."""

import json
import httpx

from .base import BaseProvider, ReviewResult

DEFAULT_BASE_URL = "https://api.mimo.xiaomi.com/v1"
DEFAULT_MODEL = "MiMo-7B"


class MiMoProvider(BaseProvider):
    """Xiaomi MiMo LLM provider for code review."""

    def __init__(
        self,
        api_key: str = "",
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
    ):
        super().__init__(api_key=api_key, model=model, base_url=base_url)

    async def review_code(self, code: str, filename: str, context: dict) -> ReviewResult:
        """Send code to MiMo for analysis."""
        prompt = self._build_prompt(code, filename, context)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are MiMo, a code review assistant by Xiaomi. Respond only in valid JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2048,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        return self._parse_response(content)

    @staticmethod
    def _parse_response(content: str) -> ReviewResult:
        """Parse LLM JSON response into ReviewResult."""
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[: -3]

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return ReviewResult(
                summary=content[:300],
                issues=[],
                suggestions=[],
                rating="N/A",
            )

        return ReviewResult(
            summary=parsed.get("summary", ""),
            issues=parsed.get("issues", []),
            suggestions=parsed.get("suggestions", []),
            rating=parsed.get("rating", "N/A"),
        )
