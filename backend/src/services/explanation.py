import json
import logging
import os
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 45.0
_SYSTEM_PROMPT = (
    "You are a Berlin rental market analyst. "
    "Your task is to explain a pricing recommendation to a landlord. "
    "Use ONLY the data provided. Do NOT invent statistics. "
    "Respond with a JSON object containing exactly two keys: "
    '"explanation" (a plain-English paragraph under 200 words) and '
    '"factors" (an array of exactly 3 objects, each with'
    ' "name", "description", and "value" keys). '
    "Do not include any text outside the JSON object."
)


@dataclass
class ExplanationResult:
    explanation_available: bool
    explanation: str | None = None
    factors: list[dict] = field(default_factory=list)


class ExplanationService:
    def __init__(self, ollama_url: str | None = None):
        self._ollama_url = ollama_url or os.environ.get(
            "OLLAMA_URL", "http://localhost:11434"
        )

    def _build_prompt(self, apartment: dict, stats: dict) -> str:
        context = {
            "apartment": {
                "address": apartment.get("address"),
                "size_m2": apartment.get("size_m2"),
                "rooms": apartment.get("rooms"),
                "floor": apartment.get("floor"),
                "amenities": apartment.get("amenities", []),
            },
            "comparables_stats": {
                "count": stats.get("comparable_count"),
                "recommended_price_eur": float(stats.get("recommended_price_eur", 0)),
                "confidence_low_eur": float(stats.get("confidence_low_eur", 0)),
                "confidence_high_eur": float(stats.get("confidence_high_eur", 0)),
                "percentile_rank": stats.get("percentile_rank"),
            },
        }
        return json.dumps(context)

    async def generate(self, apartment: dict, stats: dict) -> ExplanationResult:
        prompt = self._build_prompt(apartment, stats)
        payload = {
            # "model": "llama3.1:8b"
            "model": "qwen2.5:0.5b",
            "prompt": prompt,
            "system": _SYSTEM_PROMPT,
            "stream": False,
            "format": "json",
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(
                    f"{self._ollama_url}/api/generate", json=payload
                )
                response.raise_for_status()
                raw = response.json().get("response", "")
                parsed = json.loads(raw)
                explanation = parsed.get("explanation")
                factors = parsed.get("factors", [])
                if not explanation or len(factors) != 3:
                    raise ValueError("Response schema invalid")
                return ExplanationResult(
                    explanation_available=True,
                    explanation=explanation,
                    factors=factors,
                )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("Ollama unreachable: %s", exc)
            return ExplanationResult(explanation_available=False)
        except Exception as exc:
            logger.warning("Explanation generation failed: %s", exc)
            return ExplanationResult(explanation_available=False)
