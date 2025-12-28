"""
Testy pro SÚKL MCP Server.

Spuštění:
    pytest tests/ -v
    pytest tests/ -v --cov=sukl_mcp
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

# Import testovaných modulů
import sys
sys.path.insert(0, "src")

from sukl_mcp.models import (
    MedicineSearchResult,
    MedicineDetail,
    PharmacyInfo,
    AvailabilityInfo,
    ReimbursementInfo,
    PILContent,
    SearchResponse,
    ActiveSubstance,
    ATCGroup
)
from sukl_mcp.client import SUKLClient, SUKLConfig, MemoryCache, RateLimiter


# === Model Tests ===

class TestModels:
    """Testy pro Pydantic modely."""
    
    def test_medicine_search_result_minimal(self):
        """Test minimálního MedicineSearchResult."""
        result = MedicineSearchResult(
            sukl_code="0000001",
            name="Test Medicine"
        )
        assert result.sukl_code == "0000001"
        assert result.name == "Test Medicine"
        assert result.supplement is None
    
    def test_medicine_search_result_full(self):
        """Test kompletního MedicineSearchResult."""
        result = MedicineSearchResult(
            sukl_code="0012345",
            name="Paralen",
            supplement="500 mg",
            strength="500 mg",
            form="TBL",
            package="20",
            atc_code="N02BE01",
            registration_status="R",
            dispensation_mode="F",
            is_available=True,
            has_reimbursement=False
        )
        assert result.atc_code == "N02BE01"
        assert result.is_available is True
    
    def test_medicine_detail(self):
        """Test MedicineDetail modelu."""
        detail = MedicineDetail(
            sukl_code="0012345",
            name="Test Drug",
            strength="100 mg",
            form="TBL",
            is_available=True,
            is_marketed=True,
            has_reimbursement=True,
            max_price=150.50,
            pil_available=True,
            spc_available=True
        )
        assert detail.max_price == 150.50
        assert detail.pil_available is True
    
    def test_pharmacy_info(self):
        """Test PharmacyInfo modelu."""
        pharmacy = PharmacyInfo(
            pharmacy_id="12345",
            name="Lékárna U Zlatého hada",
            city="Praha",
            street="Karlova 15",
            postal_code="11000",
            has_24h_service=True,
            has_internet_sales=False
        )
        assert pharmacy.city == "Praha"
        assert pharmacy.has_24h_service is True
    
    def test_availability_info(self):
        """Test AvailabilityInfo."""
        avail = AvailabilityInfo(
            sukl_code="0012345",
            medicine_name="Test",
            is_available=False,
            is_marketed=True,
            unavailability_reason="Výpadek dodávek"
        )
        assert avail.is_available is False
        assert avail.unavailability_reason == "Výpadek dodávek"
    
    def test_reimbursement_info(self):
        """Test ReimbursementInfo."""
        reimb = ReimbursementInfo(
            sukl_code="0012345",
            medicine_name="Test",
            is_reimbursed=True,
            reimbursement_amount=100.0,
            patient_copay=25.0,
            has_indication_limit=True,
            indication_limit_text="Pouze pro pacienty s chronickou bolestí"
        )
        assert reimb.is_reimbursed is True
        assert reimb.patient_copay == 25.0
    
    def test_search_response(self):
        """Test SearchResponse."""
        response = SearchResponse(
            query="ibuprofen",
            total_results=5,
            results=[
                MedicineSearchResult(sukl_code="0000001", name="Ibuprofen 400"),
                MedicineSearchResult(sukl_code="0000002", name="Ibuprofen 600"),
            ],
            search_time_ms=15.5
        )
        assert response.total_results == 5
        assert len(response.results) == 2
    
    def test_active_substance(self):
        """Test ActiveSubstance."""
        substance = ActiveSubstance(
            name="Paracetamolum",
            name_en="Paracetamol",
            strength="500 mg",
            unit="mg"
        )
        assert substance.name == "Paracetamolum"
    
    def test_atc_group(self):
        """Test ATCGroup."""
        group = ATCGroup(
            code="N02BE01",
            name="Paracetamol",
            level=5
        )
        assert group.level == 5


# === Cache Tests ===

class TestMemoryCache:
    """Testy pro MemoryCache."""
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """Test základního set/get."""
        cache = MemoryCache(default_ttl=60)
        await cache.set("key1", {"data": "value"})
        result = await cache.get("key1")
        assert result == {"data": "value"}
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss."""
        cache = MemoryCache()
        result = await cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_expiry(self):
        """Test expirace cache."""
        cache = MemoryCache(default_ttl=0)  # Okamžitá expirace
        await cache.set("key", "value", ttl=0)
        # Po velmi krátké době by mělo expirovat
        import asyncio
        await asyncio.sleep(0.01)
        result = await cache.get("key")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test vymazání cache."""
        cache = MemoryCache()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
    
    def test_cache_stats(self):
        """Test statistik cache."""
        cache = MemoryCache()
        stats = cache.stats()
        assert "entries" in stats
        assert "total_hits" in stats


# === Rate Limiter Tests ===

class TestRateLimiter:
    """Testy pro RateLimiter."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests(self):
        """Test že rate limiter povolí requesty pod limitem."""
        limiter = RateLimiter(max_requests=10, period_seconds=1)
        
        # 5 requestů by mělo projít okamžitě
        for _ in range(5):
            await limiter.acquire()
        
        assert len(limiter.requests) == 5
    
    @pytest.mark.asyncio
    async def test_rate_limiter_cleans_old_requests(self):
        """Test čištění starých requestů."""
        limiter = RateLimiter(max_requests=10, period_seconds=1)
        
        # Přidej pár requestů
        await limiter.acquire()
        await limiter.acquire()
        
        # Počkej na expiraci
        import asyncio
        await asyncio.sleep(1.1)
        
        # Další request by měl vyčistit staré
        await limiter.acquire()
        
        # Měl by zůstat jen jeden nový
        assert len(limiter.requests) == 1


# === Client Tests ===

class TestSUKLClient:
    """Testy pro SUKLClient."""
    
    def test_config_defaults(self):
        """Test výchozí konfigurace."""
        config = SUKLConfig()
        assert config.api_base_url == "https://prehledy.sukl.cz/prehledy/v1"
        assert config.cache_enabled is True
        assert config.max_retries == 3
    
    def test_config_custom(self):
        """Test vlastní konfigurace."""
        config = SUKLConfig(
            timeout_seconds=60.0,
            cache_ttl_seconds=7200,
            max_retries=5
        )
        assert config.timeout_seconds == 60.0
        assert config.cache_ttl_seconds == 7200
    
    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test context manager."""
        async with SUKLClient() as client:
            assert client._client is not None
        # Po ukončení by měl být client None
        assert client._client is None
    
    @pytest.mark.asyncio
    async def test_client_search_medicines_mock(self):
        """Test vyhledávání s mocknutým HTTP."""
        mock_response = [
            {"kod_sukl": "0012345", "nazev": "Paralen", "atc": "N02BE01"}
        ]
        
        async with SUKLClient() as client:
            with patch.object(client, '_api_request', new_callable=AsyncMock) as mock:
                mock.return_value = mock_response
                
                results = await client.search_medicines("paralen")
                
                assert len(results) == 1
                assert results[0]["nazev"] == "Paralen"
    
    @pytest.mark.asyncio
    async def test_client_get_medicine_detail_mock(self):
        """Test detailu léčiva s mockem."""
        mock_detail = {
            "kod_sukl": "0012345",
            "nazev": "Paralen 500",
            "sila": "500 mg",
            "dostupnost": "ano"
        }
        
        async with SUKLClient() as client:
            with patch.object(client, '_api_request', new_callable=AsyncMock) as mock:
                mock.return_value = mock_detail
                
                result = await client.get_medicine_detail("0012345")
                
                assert result["nazev"] == "Paralen 500"
    
    @pytest.mark.asyncio
    async def test_client_search_pharmacies_mock(self):
        """Test vyhledávání lékáren s mockem."""
        mock_pharmacies = [
            {"id_lekarny": "1", "nazev": "Lékárna Praha", "mesto": "Praha"}
        ]
        
        async with SUKLClient() as client:
            with patch.object(client, '_api_request', new_callable=AsyncMock) as mock:
                mock.return_value = mock_pharmacies
                
                results = await client.search_pharmacies(city="Praha")
                
                assert len(results) == 1
                assert results[0]["mesto"] == "Praha"
    
    @pytest.mark.asyncio
    async def test_client_health_check_mock(self):
        """Test health check."""
        async with SUKLClient() as client:
            with patch.object(client, '_api_request', new_callable=AsyncMock) as mock_api:
                mock_api.return_value = {"status": "ok"}
                
                with patch.object(client.client, 'head', new_callable=AsyncMock) as mock_head:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_head.return_value = mock_response
                    
                    health = await client.health_check()
                    
                    assert "api_available" in health
                    assert "timestamp" in health


# === Integration Tests (require network) ===

@pytest.mark.integration
class TestIntegration:
    """Integrační testy vyžadující síťové připojení."""
    
    @pytest.mark.asyncio
    async def test_real_api_health(self):
        """Test skutečného API health check."""
        async with SUKLClient() as client:
            health = await client.health_check()
            # Alespoň jeden zdroj by měl být dostupný
            assert health.get("api_available") or health.get("opendata_available")
    
    @pytest.mark.asyncio
    async def test_real_search(self):
        """Test skutečného vyhledávání."""
        async with SUKLClient() as client:
            # Toto může selhat pokud API není dostupné
            try:
                results = await client.search_medicines("ibuprofen", limit=5)
                assert isinstance(results, list)
            except Exception:
                pytest.skip("API není dostupné")


# === Server Tool Tests ===

class TestServerTools:
    """Testy pro MCP nástroje (mocknuté)."""
    
    @pytest.mark.asyncio
    async def test_search_medicine_tool(self):
        """Test search_medicine nástroje."""
        from sukl_mcp.server import search_medicine
        
        with patch('sukl_mcp.server.get_sukl_client', new_callable=AsyncMock) as mock:
            mock_client = AsyncMock()
            mock_client.search_medicines.return_value = [
                {"kod_sukl": "0012345", "nazev": "Test Drug", "atc": "N02BE01"}
            ]
            mock.return_value = mock_client
            
            result = await search_medicine("test", limit=10)
            
            assert result.query == "test"
            assert result.total_results == 1
    
    @pytest.mark.asyncio
    async def test_find_pharmacies_tool(self):
        """Test find_pharmacies nástroje."""
        from sukl_mcp.server import find_pharmacies
        
        with patch('sukl_mcp.server.get_sukl_client', new_callable=AsyncMock) as mock:
            mock_client = AsyncMock()
            mock_client.search_pharmacies.return_value = [
                {"id_lekarny": "1", "nazev": "Test Pharmacy", "mesto": "Praha"}
            ]
            mock.return_value = mock_client
            
            results = await find_pharmacies(city="Praha")
            
            assert len(results) == 1
            assert results[0].city == "Praha"


# === Fixtures ===

@pytest.fixture
def sample_medicine_data():
    """Ukázková data léčiva."""
    return {
        "kod_sukl": "0012345",
        "nazev": "Paralen",
        "doplnek": "500 mg tablety",
        "sila": "500 mg",
        "forma": "TBL NOB",
        "baleni": "24",
        "atc": "N02BE01",
        "stav_registrace": "R",
        "vydej": "F",
        "dostupnost": "ano",
        "uhrada": "ne"
    }


@pytest.fixture
def sample_pharmacy_data():
    """Ukázková data lékárny."""
    return {
        "id_lekarny": "12345",
        "nazev": "Lékárna U Zlatého hada",
        "ulice": "Karlova 15",
        "mesto": "Praha 1",
        "psc": "11000",
        "telefon": "+420 222 222 222",
        "nepretrzity_provoz": "ne",
        "internetovy_prodej": "ano"
    }


# === Run Tests ===

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
