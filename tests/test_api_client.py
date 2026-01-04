"""
Testy pro SÚKL API klient.

Obsahuje:
- Unit testy s mockovaným HTTP
- Integration testy proti reálnému API (označené @pytest.mark.integration)
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from sukl_mcp.api.client import SUKLAPIClient, SUKLAPIConfig, CacheEntry
from sukl_mcp.api.models import APILecivyPripravek, APISearchResponse
from sukl_mcp.exceptions import SUKLAPIError, SUKLValidationError


# === Fixtures ===


@pytest.fixture
def config() -> SUKLAPIConfig:
    """Testovací konfigurace."""
    return SUKLAPIConfig(
        base_url="https://prehledy.sukl.cz",
        timeout=10.0,
        max_retries=2,
        retry_delay=0.1,
        cache_ttl=60,
        rate_limit=100,
    )


@pytest.fixture
def mock_medicine_response() -> dict:
    """Mock response pro detail léčiva."""
    return {
        "kodSUKL": "0254045",
        "nazev": "PARALEN",
        "sila": "500MG",
        "lekovaFormaKod": "TBL NOB",
        "baleni": "10",
        "ATCkod": "N02BE01",
        "stavRegistraceKod": "R",
        "jeDodavka": True,
        "leciveLatky": [1064],
        "zpusobVydejeKod": "V",
    }


@pytest.fixture
def mock_search_response() -> list:
    """Mock response pro vyhledávání."""
    return ["0254045", "0254046", "0254047"]


# === Unit Tests ===


class TestSUKLAPIConfig:
    """Testy pro konfiguraci."""
    
    def test_default_config(self):
        """Test výchozí konfigurace."""
        config = SUKLAPIConfig()
        assert config.base_url == "https://prehledy.sukl.cz"
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.cache_ttl == 300
    
    def test_custom_config(self):
        """Test vlastní konfigurace."""
        config = SUKLAPIConfig(timeout=60.0, cache_ttl=600)
        assert config.timeout == 60.0
        assert config.cache_ttl == 600


class TestCacheEntry:
    """Testy pro cache entry."""
    
    def test_valid_entry(self):
        """Test platné cache entry."""
        entry = CacheEntry(data={"test": 1}, timestamp=time.time())
        assert entry.is_valid(ttl=60) is True
    
    def test_expired_entry(self):
        """Test expirované cache entry."""
        entry = CacheEntry(data={"test": 1}, timestamp=time.time() - 100)
        assert entry.is_valid(ttl=60) is False


class TestSUKLAPIClientInit:
    """Testy pro inicializaci klienta."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self, config: SUKLAPIConfig):
        """Test async context manager."""
        async with SUKLAPIClient(config) as client:
            assert client._client is not None
            assert client._closed is False
        
        assert client._closed is True
    
    @pytest.mark.asyncio
    async def test_close(self, config: SUKLAPIConfig):
        """Test uzavření klienta."""
        client = SUKLAPIClient(config)
        await client._ensure_client()
        assert client._client is not None
        
        await client.close()
        assert client._closed is True


class TestSearchMedicines:
    """Testy pro vyhledávání léčiv."""
    
    @pytest.mark.asyncio
    async def test_search_success(
        self,
        config: SUKLAPIConfig,
        mock_search_response: list,
    ):
        """Test úspěšného vyhledávání."""
        with patch.object(SUKLAPIClient, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_search_response
            
            async with SUKLAPIClient(config) as client:
                result = await client.search_medicines("PARALEN")
            
            assert isinstance(result, APISearchResponse)
            assert len(result.codes) == 3
            assert result.total == 3
            mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self, config: SUKLAPIConfig):
        """Test prázdného dotazu."""
        async with SUKLAPIClient(config) as client:
            with pytest.raises(SUKLValidationError):
                await client.search_medicines("")
    
    @pytest.mark.asyncio
    async def test_search_with_limit(
        self,
        config: SUKLAPIConfig,
        mock_search_response: list,
    ):
        """Test s limitem."""
        with patch.object(SUKLAPIClient, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_search_response
            
            async with SUKLAPIClient(config) as client:
                result = await client.search_medicines("PARALEN", limit=2)
            
            assert len(result.codes) == 2


class TestGetMedicine:
    """Testy pro získání detailu léčiva."""
    
    @pytest.mark.asyncio
    async def test_get_success(
        self,
        config: SUKLAPIConfig,
        mock_medicine_response: dict,
    ):
        """Test úspěšného získání detailu."""
        with patch.object(SUKLAPIClient, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_medicine_response
            
            async with SUKLAPIClient(config) as client:
                result = await client.get_medicine("0254045")
            
            assert result is not None
            assert result.kodSUKL == "0254045"
            assert result.nazev == "PARALEN"
            assert result.jeDodavka is True
    
    @pytest.mark.asyncio
    async def test_get_invalid_code(self, config: SUKLAPIConfig):
        """Test neplatného kódu."""
        async with SUKLAPIClient(config) as client:
            with pytest.raises(SUKLValidationError):
                await client.get_medicine("invalid")
    
    @pytest.mark.asyncio
    async def test_get_not_found(self, config: SUKLAPIConfig):
        """Test neexistujícího léčiva."""
        with patch.object(SUKLAPIClient, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = SUKLAPIError("HTTP 404: not found")
            
            async with SUKLAPIClient(config) as client:
                result = await client.get_medicine("9999999")
            
            assert result is None


class TestCache:
    """Testy pro caching."""
    
    @pytest.mark.asyncio
    async def test_cache_hit(
        self,
        config: SUKLAPIConfig,
        mock_medicine_response: dict,
    ):
        """Test cache hit - ověření, že cache funguje."""
        async with SUKLAPIClient(config) as client:
            # Vložíme data do cache přímo
            cache_key = "detail_0254045"
            client._cache[cache_key] = CacheEntry(
                data=mock_medicine_response,
                timestamp=time.time()
            )
            
            # Request by měl jít z cache
            result = await client.get_medicine("0254045")
            
            assert result is not None
            assert result.kodSUKL == "0254045"
            
            # Ověříme, že cache byla použita (klíč stále existuje)
            assert cache_key in client._cache
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, config: SUKLAPIConfig):
        """Test vymazání cache."""
        async with SUKLAPIClient(config) as client:
            client._cache["test"] = CacheEntry(data={}, timestamp=time.time())
            assert len(client._cache) == 1
            
            client.clear_cache()
            assert len(client._cache) == 0
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, config: SUKLAPIConfig):
        """Test statistik cache."""
        async with SUKLAPIClient(config) as client:
            client._cache["valid"] = CacheEntry(data={}, timestamp=time.time())
            client._cache["stale"] = CacheEntry(data={}, timestamp=time.time() - 1000)
            
            stats = client.get_cache_stats()
            assert stats["total_entries"] == 2
            assert stats["valid_entries"] == 1
            assert stats["stale_entries"] == 1


class TestRateLimiting:
    """Testy pro rate limiting."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_tracking(self, config: SUKLAPIConfig):
        """Test sledování počtu requestů."""
        config.rate_limit = 5
        
        async with SUKLAPIClient(config) as client:
            # Simulace requestů
            for _ in range(3):
                await client._check_rate_limit()
            
            assert client._request_count == 3


class TestHealthCheck:
    """Testy pro health check."""
    
    @pytest.mark.asyncio
    async def test_health_check_success(
        self,
        config: SUKLAPIConfig,
        mock_medicine_response: dict,
    ):
        """Test úspěšného health checku."""
        with patch.object(SUKLAPIClient, "get_medicine", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = APILecivyPripravek(**mock_medicine_response)
            
            async with SUKLAPIClient(config) as client:
                result = await client.health_check()
            
            assert result["status"] == "healthy"
            assert result["api_available"] is True
            assert "latency_ms" in result
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, config: SUKLAPIConfig):
        """Test selhání health checku."""
        with patch.object(SUKLAPIClient, "get_medicine", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection failed")
            
            async with SUKLAPIClient(config) as client:
                result = await client.health_check()
            
            assert result["status"] == "unhealthy"
            assert result["api_available"] is False


# === Integration Tests ===


@pytest.mark.integration
class TestIntegration:
    """
    Integrační testy proti reálnému SÚKL API.
    
    Spouštějte s: pytest -m integration
    """
    
    @pytest.mark.asyncio
    async def test_real_search(self):
        """Test reálného vyhledávání."""
        async with SUKLAPIClient() as client:
            result = await client.search_medicines("PARALEN", limit=5)
            
            assert result.total > 0
            assert len(result.codes) <= 5
    
    @pytest.mark.asyncio
    async def test_real_get_medicine(self):
        """Test reálného získání detailu."""
        async with SUKLAPIClient() as client:
            medicine = await client.get_medicine("0254045")
            
            assert medicine is not None
            assert medicine.nazev == "PARALEN"
            assert medicine.ATCkod == "N02BE01"
    
    @pytest.mark.asyncio
    async def test_real_health_check(self):
        """Test reálného health checku."""
        async with SUKLAPIClient() as client:
            result = await client.health_check()
            
            assert result["status"] in ["healthy", "degraded"]
            assert "latency_ms" in result
    
    @pytest.mark.asyncio
    async def test_real_batch_fetch(self):
        """Test batch fetch."""
        async with SUKLAPIClient() as client:
            codes = ["0254045", "0001234", "9999999"]  # PARALEN, jiný, neexistující
            results = await client.get_medicines_batch(codes, max_concurrent=2)
            
            # Alespoň PARALEN by měl existovat
            assert len(results) >= 1
            assert any(m.kodSUKL == "0254045" for m in results)
