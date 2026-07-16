"""T033 — Unit tests for explanation service.

Written before implementation (TDD red phase).
src.services.explanation does not exist yet.
Ollama HTTP calls are mocked.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.explanation import ExplanationService

STATS = {
    "comparable_count": 15,
    "recommended_price_eur": Decimal("1250.00"),
    "confidence_low_eur": Decimal("1100.00"),
    "confidence_high_eur": Decimal("1420.00"),
    "percentile_rank": 58.3,
}

APARTMENT = {
    "address": "Invalidenstraße 50, 10115 Berlin",
    "size_m2": 72.0,
    "rooms": 3.0,
    "floor": 2,
    "amenities": ["balcony"],
}

_EXP = "Based on 15 comparables in Mitte, the median price is €1,250/month."
_F1 = (
    '{"name":"Market Median","description":"15 comparables median €1,250",'
    '"value":"€1,250/month"}'
)
_F2 = '{"name":"Supply Level","description":"15 active listings","value":"15 listings"}'
_F3 = '{"name":"Price Range","description":"IQR €1,100–€1,420","value":"€1,100–€1,420"}'
VALID_OLLAMA_RESPONSE = {
    "response": f'{{"explanation":"{_EXP}","factors":[{_F1},{_F2},{_F3}]}}'
}


class TestExplanationService:
    @pytest.fixture
    def service(self):
        return ExplanationService(ollama_url="http://localhost:11434")

    @patch("src.services.explanation.httpx.AsyncClient")
    async def test_returns_explanation_and_three_factors(
        self, mock_client_cls, service
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = VALID_OLLAMA_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await service.generate(apartment=APARTMENT, stats=STATS)
        assert result.explanation_available is True
        assert len(result.explanation) > 0
        assert len(result.factors) == 3
        for factor in result.factors:
            assert "name" in factor
            assert "description" in factor
            assert "value" in factor

    @patch("src.services.explanation.httpx.AsyncClient")
    async def test_graceful_fallback_when_ollama_unreachable(
        self, mock_client_cls, service
    ):
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        mock_client_cls.return_value = mock_client

        result = await service.generate(apartment=APARTMENT, stats=STATS)
        assert result.explanation_available is False
        assert result.explanation is None
        assert result.factors == []

    @patch("src.services.explanation.httpx.AsyncClient")
    async def test_graceful_fallback_on_timeout(self, mock_client_cls, service):
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client_cls.return_value = mock_client

        result = await service.generate(apartment=APARTMENT, stats=STATS)
        assert result.explanation_available is False

    @patch("src.services.explanation.httpx.AsyncClient")
    async def test_graceful_fallback_when_response_schema_invalid(
        self, mock_client_cls, service
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "not valid json at all"}
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await service.generate(apartment=APARTMENT, stats=STATS)
        assert result.explanation_available is False

    def test_prompt_includes_comparable_count(self, service):
        prompt = service._build_prompt(apartment=APARTMENT, stats=STATS)
        assert "15" in prompt

    def test_prompt_includes_recommended_price(self, service):
        prompt = service._build_prompt(apartment=APARTMENT, stats=STATS)
        assert "1250" in prompt or "1,250" in prompt
