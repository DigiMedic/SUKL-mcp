"""
Unit testy pro SUKL REST API klienta.

Testuje metody z src/sukl_mcp/api/client.py.
"""

import pytest
from unittest.mock import AsyncMock, patch

from sukl_mcp.api.client import (
    SUKLAPIClient,
    SUKLAPIConfig,
    get_rest_client,
    close_rest_client,
)
from sukl_mcp.api.rest_models import (
    DLPResponse,
    LekarnyResponse,
    CiselnikResponse,
    DatumAktualizace,
    DLPSearchParams,
)
from sukl_mcp.exceptions import SUKLAPIError, SUKLValidationError


@pytest.fixture
async def client():
    """Fixture pro vytvoření REST API klienta."""
    config = SUKLAPIConfig(timeout=5.0)
    async with SUKLAPIClient(config) as c:
        yield c


@pytest.mark.asyncio
async def test_search_medicines_by_atc(client):
    """Test vyhledávání léků podle ATC kódu."""
    with patch.object(client, "_request", new=AsyncMock()) as mock_request:
        mock_response = {
            "data": [
                {
                    "kodSUKL": "0209084",
                    "nazevLP": "ABASAGLAR",
                    "registracniCisloDisplay": "EU/1/14/944/008",
                    "stavRegistrace": "R",
                    "jeDodavka": True,
                    "atc": {
                        "kod": "A10AE04",
                        "nazev": {"cs": "INSULIN GLARGIN", "en": "INSULIN GLARGINE"},
                    },
                }
            ],
            "celkem": 1,
            "extraSearch": [],
        }
        mock_request.return_value = mock_response

        result = await client.search_medicines(atc="A10AE04", pocet=1)

        assert isinstance(result, DLPResponse)
        assert result.celkem == 1
        assert len(result.data) == 1
        assert result.data[0].kodSUKL == "0209084"
        assert result.data[0].nazevLP == "ABASAGLAR"


@pytest.mark.asyncio
async def test_search_medicines_by_stav_registrace(client):
    """Test vyhledávání léků podle stavu registrace."""
    with patch.object(client, "_request", new=AsyncMock()) as mock_request:
        mock_response = {
            "data": [{"kodSUKL": "0094156", "nazevLP": "ABAKTAL", "stavRegistrace": "R"}],
            "celkem": 58,
            "extraSearch": [],
        }
        mock_request.return_value = mock_response

        result = await client.search_medicines(stav_registrace="R", pocet=5)

        assert result.celkem == 58
        assert all(m["stavRegistrace"] == "R" for m in result.data)


@pytest.mark.asyncio
async def test_search_medicines_by_uhrada(client):
    """Test vyhledávání léků podle úhrady."""
    with patch.object(client, "_request", new=AsyncMock()) as mock_request:
        mock_response = {
            "data": [{"kodSUKL": "0094156", "uhrada": "A"}],
            "celkem": 10,
            "extraSearch": [],
        }
        mock_request.return_value = mock_response

        result = await client.search_medicines(uhrada="A", pocet=5)

        assert result.celkem == 10


@pytest.mark.asyncio
async def test_search_medicines_pagination(client):
    """Test stránkování vyhledávání léků."""
    with patch.object(client, "_request", new=AsyncMock()) as mock_request:
        mock_response_page1 = {"data": [{"kodSUKL": "001"}], "celkem": 100, "extraSearch": []}
        mock_response_page2 = {"data": [{"kodSUKL": "002"}], "celkem": 100, "extraSearch": []}
        mock_request.side_effect = [mock_response_page1, mock_response_page2]

        result1 = await client.search_medicines(stranka=1, pocet=1)
        result2 = await client.search_medicines(stranka=2, pocet=1)

        assert result1.data[0]["kodSUKL"] == "001"
        assert result2.data[0]["kodSUKL"] == "002"


@pytest.mark.asyncio
async def test_search_medicines_validation_error(client):
    """Test validace vstupních parametrů - invalid stranka."""
    with pytest.raises(SUKLValidationError):
        await client.search_medicines(stranka=0)


@pytest.mark.asyncio
async def test_search_medicines_validation_error_pocet(client):
    """Test validace vstupních parametrů - invalid pocet."""
    with pytest.raises(SUKLValidationError):
        await client.search_medicines(pocet=1001)


@pytest.mark.asyncio
async def test_search_medicines_api_error(client):
    """Test zpracování API chyb."""
    with patch.object(client, "_request", side_effect=SUKLAPIError("API Error", 500)):
        with pytest.raises(SUKLAPIError):
            await client.search_medicines(atc="A10AE04")


@pytest.mark.asyncio
async def test_get_pharmacies(client):
    """Test získání seznamu lékáren."""
    with patch.object(client, "_request", new=AsyncMock()) as mock_request:
        mock_response = {
            "data": [
                {
                    "nazev": "Horská lékárna s.r.o.",
                    "kodLekarny": "67995050",
                    "adresa": {"obec": "Rokytnice nad Jizerou", "psc": "51244"},
                }
            ],
            "celkem": 4896,
        }
        mock_request.return_value = mock_response

        result = await client.get_pharmacies(stranka=1, pocet=5)

        assert isinstance(result, LekarnyResponse)
        assert result.celkem == 4896
        assert len(result.data) == 5
        assert result.data[0].nazev == "Horská lékárna s.r.o."


@pytest.mark.asyncio
async def test_get_pharmacy_detail(client):
    """Test získání detailu lékárny."""
    with patch.object(client, "_request", new=AsyncMock()) as mock_request:
        mock_response = {
            "nazev": "Horská lékárna s.r.o.",
            "kodLekarny": "67995050",
            "adresa": {
                "obec": "Rokytnice nad Jizerou",
                "ulice": "Horní Rokytnice",
                "cisloPopisne": "275",
            },
        }
        mock_request.return_value = mock_response

        result = await client.get_pharmacy_detail("67995050")

        assert result.nazev == "Horská lékárna s.r.o."
        assert result.kodLekarny == "67995050"


@pytest.mark.asyncio
async def test_get_ciselnik(client):
    """Test získání číselníku."""
    with patch.object(client, "_request", new=AsyncMock()) as mock_request:
        mock_response = [
            {"kod": "POR", "nazev": "Perorální podání"},
            {"kod": "IVN", "nazev": "Intravenózní podání"},
        ]
        mock_request.return_value = mock_response

        result = await client.get_ciselnik("cesty_podani")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["kod"] == "POR"


@pytest.mark.asyncio
async def test_get_atc_codes(client):
    """Test získání ATC kódů."""
    with patch.object(client, "_request", new=AsyncMock()) as mock_request:
        mock_response = [
            {"kod": "A07EC01", "nazev": "SULFASALAZIN"},
            {"kod": "A02BC01", "nazev": "CIMETIDIN"},
        ]
        mock_request.return_value = mock_response

        result = await client.get_atc_codes()

        assert isinstance(result, list)
        assert len(result) == 2


@pytest.mark.asyncio
async def test_get_update_dates(client):
    """Test získání data aktualizace."""
    with patch.object(client, "_request", new=AsyncMock()) as mock_request:
        mock_response = {
            "DLPO": "2025-12-01 00:00:00",
            "DLPW": "2026-01-05 23:00:00",
            "SCAU": "2026-01-01 00:00:00",
        }
        mock_request.return_value = mock_response

        result = await client.get_update_dates()

        assert isinstance(result, DatumAktualizace)
        assert result.DLPO == "2025-12-01 00:00:00"
        assert result.DLPW == "2026-01-05 23:00:00"
        assert result.SCAU == "2026-01-01 00:00:00"


@pytest.mark.asyncio
async def test_cache_mechanism(client):
    """Test mechanismu cache."""
    from sukl_mcp.api.client import CacheEntry
    import time

    cache_key = "test_key"
    test_data = {"test": "data"}
    client._cache[cache_key] = CacheEntry(data=test_data, timestamp=time.time())

    assert len(client._cache) == 1
    assert cache_key in client._cache
    assert client._cache[cache_key].data == test_data


@pytest.mark.asyncio
async def test_clear_cache(client):
    """Test vymazání cache."""
    from sukl_mcp.api.client import CacheEntry
    import time

    client._cache["test_key1"] = CacheEntry(data={"test": 1}, timestamp=time.time())
    client._cache["test_key2"] = CacheEntry(data={"test": 2}, timestamp=time.time())
    assert len(client._cache) > 0

    client.clear_cache()
    assert len(client._cache) == 0


@pytest.mark.asyncio
async def test_cache_stats(client):
    """Test statistik cache."""
    with patch.object(client, "_request", new=AsyncMock()):
        result = client.get_cache_stats()
        assert "total_entries" in result
        assert "valid_entries" in result
        assert "stale_entries" in result


@pytest.mark.asyncio
async def test_health_check_healthy(client):
    """Test health check při dostupném API."""
    with patch.object(client, "get_pharmacies", new=AsyncMock()) as mock_pharmacies:
        from sukl_mcp.api.rest_models import LekarnyResponse, Lekarna

        mock_pharmacy = Lekarna(nazev="Test")
        mock_response = LekarnyResponse(data=[mock_pharmacy], celkem=1)
        mock_pharmacies.return_value = mock_response

        result = await client.health_check()
        assert result["status"] == "healthy"
        assert result["api_available"] is True


@pytest.mark.asyncio
async def test_health_check_unhealthy(client):
    """Test health check při nedostupném API."""
    with patch.object(client, "_request", side_effect=Exception("Connection error")):
        result = await client.health_check()
        assert result["status"] == "unhealthy"
        assert result["api_available"] is False


@pytest.mark.asyncio
async def test_rate_limiting(client):
    """Test rate limiting mechanismu."""
    config = SUKLAPIConfig(rate_limit=2)
    async with SUKLAPIClient(config) as limited_client:
        with patch.object(
            limited_client,
            "_request",
            new=AsyncMock(return_value={"data": [], "celkem": 0, "extraSearch": []}),
        ):
            await limited_client.search_medicines(atc="A10AE04")
            assert limited_client._request_count == 1

            await limited_client.search_medicines(atc="A10AE04")
            await limited_client.search_medicines(atc="A10AE04")
            assert limited_client._request_count == 2

            await limited_client.search_medicines(atc="A10AE04")
            assert limited_client._request_count == 2


@pytest.mark.asyncio
async def test_singleton_pattern():
    """Test singleton pattern pro globální klienta."""
    client1 = await get_rest_client()
    client2 = await get_rest_client()
    assert client1 is client2

    await close_rest_client()
    new_client = await get_rest_client()
    assert new_client is not client1


@pytest.mark.asyncio
async def test_context_manager():
    """Test async context manager."""
    config = SUKLAPIConfig(timeout=5.0)
    async with SUKLAPIClient(config) as client:
        assert client._client is not None
        assert not client._closed

    assert client._closed


@pytest.mark.asyncio
async def test_custom_config():
    """Test použití vlastní konfigurace."""
    config = SUKLAPIConfig(
        base_url="https://test.example.com",
        timeout=10.0,
        max_retries=5,
        cache_ttl=600,
    )

    assert config.base_url == "https://test.example.com"
    assert config.timeout == 10.0
    assert config.max_retries == 5
    assert config.cache_ttl == 600


@pytest.mark.asyncio
async def test_close_client(client):
    """Test zavření klienta."""
    assert client._client is not None

    await client.close()

    assert client._closed
    assert client._client is None
