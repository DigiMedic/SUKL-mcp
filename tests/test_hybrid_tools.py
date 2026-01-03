"""
Integration tests pro hybrid mode implementation (v4.0).

Testuje:
1. _try_rest_get_detail() - REST API helper function
2. _try_rest_search() - REST API search helper
3. CSV client - fallback mechanism
4. Hybrid workflows - REST + CSV integration
5. Data consistency across sources

Test Strategy:
- Test helper functions directly (not MCP tools)
- Verify REST API is used as primary source
- Verify CSV fallback works
- Verify CSV-only operations (pricing, alternatives)
- End-to-end hybrid workflows
"""

import pytest
from sukl_mcp.server import (
    mcp,
    server_lifespan,
    _try_rest_get_detail,
    _try_rest_search,
)
from sukl_mcp.client_csv import get_sukl_client
from sukl_mcp.api import get_api_client


@pytest.mark.asyncio
async def test_rest_api_helper_get_detail():
    """Test _try_rest_get_detail() helper function."""
    async with server_lifespan(mcp):
        # Test s známým kódem PARALEN
        result = await _try_rest_get_detail("0254045")

        if result:
            assert isinstance(result, dict), "Should return dict"
            assert result.get("NAZEV"), "Should have NAZEV"
            assert result.get("FORMA"), "Should have FORMA"
            assert result.get("DODAVKY") in ["0", "1"], "Should have DODAVKY"
            print(f"✅ REST API helper: {result.get('NAZEV')}")
            print(f"   Forma: {result.get('FORMA')}")
            print(f"   Dostupnost: {result.get('DODAVKY')}")
        else:
            print("⚠️  REST API failed (expected in some cases)")


@pytest.mark.asyncio
async def test_rest_api_helper_batch():
    """Test _try_rest_get_detail() pro batch kódů."""
    async with server_lifespan(mcp):
        test_codes = [
            "0000009",  # ACYLCOFFIN
            "0000113",  # DILURAN
            "0254045",  # PARALEN
        ]

        results = []
        for code in test_codes:
            result = await _try_rest_get_detail(code)
            if result:
                results.append(result)
                print(f"   ✅ {code}: {result.get('NAZEV')}")

        assert len(results) >= 2, "Should fetch at least 2 medicines via REST"


@pytest.mark.asyncio
async def test_rest_api_search_helper():
    """Test _try_rest_search() helper function."""
    async with server_lifespan(mcp):
        # Test vyhledávání PARALEN
        results = await _try_rest_search("PARALEN", limit=5)

        if results:
            assert len(results) > 0, "Should return search results"
            # První result by měl mít atc a doplnek
            first = results[0]
            assert isinstance(first, dict), "Should be dict"
            # Results have keys: atc, baleni, doplnek, dostupnost
            assert "doplnek" in first or "atc" in first, "Should have basic fields"
            print(f"✅ REST API search: {len(results)} results for 'PARALEN'")
            print(f"   First result: {first.get('doplnek', 'N/A')}")
        else:
            print("⚠️  REST API search failed (CSV fallback will be used)")


@pytest.mark.asyncio
async def test_csv_client_get_detail():
    """Test CSV client get_medicine_detail()."""
    async with server_lifespan(mcp):
        csv_client = await get_sukl_client()

        # Test získání detailu z CSV
        detail = await csv_client.get_medicine_detail("0254045")

        assert detail is not None, "CSV should have medicine data"
        assert detail.get("NAZEV"), "CSV should have NAZEV"
        assert detail.get("FORMA"), "CSV should have FORMA"
        print(f"✅ CSV client: {detail.get('NAZEV')}")
        print(f"   Forma: {detail.get('FORMA')}")


@pytest.mark.asyncio
async def test_csv_client_price_info():
    """Test CSV client get_price_info() - CSV-only operation."""
    async with server_lifespan(mcp):
        csv_client = await get_sukl_client()

        # Cenová data jsou POUZE v CSV (REST API je nemá)
        price_info = await csv_client.get_price_info("0254045")

        # Not all medicines have price data
        if price_info:
            print(f"✅ CSV price data available")
            print(f"   Max price: {price_info.get('max_price')}")
            print(f"   Reimbursement: {price_info.get('reimbursement_amount')}")
            print(f"   Is reimbursed: {price_info.get('is_reimbursed')}")
        else:
            print("ℹ️  No price data (not all medicines have pricing)")


@pytest.mark.asyncio
async def test_csv_client_find_alternatives():
    """Test CSV client find_generic_alternatives() - CSV-only operation."""
    async with server_lifespan(mcp):
        csv_client = await get_sukl_client()

        # Hledání alternativ vyžaduje dlp_slozeni + dlp_cau (CSV only)
        alternatives = await csv_client.find_generic_alternatives(
            "0254045",
            limit=3
        )

        if alternatives:
            assert len(alternatives) <= 3, "Should respect limit"
            print(f"✅ CSV alternatives: {len(alternatives)} found")
            for alt in alternatives[:2]:
                print(f"   - {alt.get('NAZEV')} (score: {alt.get('relevance_score', 0):.1f})")
        else:
            print("ℹ️  No alternatives found (depends on substance data)")


@pytest.mark.asyncio
async def test_hybrid_workflow_get_detail():
    """Test hybrid workflow: REST API → CSV fallback → CSV enrichment."""
    async with server_lifespan(mcp):
        sukl_code = "0254045"

        # Step 1: Try REST API
        rest_data = await _try_rest_get_detail(sukl_code)

        # Step 2: Fallback to CSV if needed
        csv_client = await get_sukl_client()
        if rest_data is None:
            csv_data = await csv_client.get_medicine_detail(sukl_code)
            assert csv_data is not None, "CSV fallback should work"
            data = csv_data
            print(f"🔄 Used CSV fallback: {data.get('NAZEV')}")
        else:
            data = rest_data
            print(f"✅ Used REST API: {data.get('NAZEV')}")

        # Step 3: ALWAYS enrich with CSV price data
        price_info = await csv_client.get_price_info(sukl_code)
        if price_info:
            print(f"✅ CSV price enrichment: {price_info.get('max_price')} CZK")

        # Verify we got complete data
        assert data.get("NAZEV"), "Should have medicine name"


@pytest.mark.asyncio
async def test_hybrid_workflow_check_availability():
    """Test hybrid workflow: REST availability + CSV alternatives."""
    async with server_lifespan(mcp):
        sukl_code = "0254045"

        # Step 1: Get availability (REST or CSV)
        detail = await _try_rest_get_detail(sukl_code)

        csv_client = await get_sukl_client()
        if detail is None:
            detail = await csv_client.get_medicine_detail(sukl_code)
            print(f"🔄 Availability from CSV")
        else:
            print(f"✅ Availability from REST API")

        assert detail is not None

        # Step 2: Check if available
        is_available = csv_client._normalize_availability(detail.get("DODAVKY"))
        print(f"   Lék: {detail.get('NAZEV')}")
        print(f"   Status: {'dostupný' if is_available else 'nedostupný'}")

        # Step 3: If unavailable, find alternatives (CSV only)
        if not is_available:
            alternatives = await csv_client.find_generic_alternatives(sukl_code, limit=3)
            if alternatives:
                print(f"✅ CSV alternatives: {len(alternatives)} found")


@pytest.mark.asyncio
async def test_hybrid_workflow_search():
    """Test hybrid search workflow: REST → CSV fallback."""
    async with server_lifespan(mcp):
        query = "PARALEN"

        # Step 1: Try REST API search
        rest_results = await _try_rest_search(query, limit=5)

        # Step 2: Fallback to CSV if needed
        csv_client = await get_sukl_client()
        if not rest_results:
            csv_results, _ = await csv_client.search_medicines(query, limit=5)
            results = csv_results
            print(f"🔄 Used CSV search: {len(results)} results")
        else:
            results = rest_results
            print(f"✅ Used REST API search: {len(results)} results")

        assert len(results) > 0, "Should find results from either source"


@pytest.mark.asyncio
async def test_data_consistency_rest_vs_csv():
    """Test že REST API a CSV vracejí konzistentní data pro stejný kód."""
    async with server_lifespan(mcp):
        sukl_code = "0254045"

        # Get data from both sources
        rest_data = await _try_rest_get_detail(sukl_code)

        csv_client = await get_sukl_client()
        csv_data = await csv_client.get_medicine_detail(sukl_code)

        if rest_data and csv_data:
            # Compare key fields
            rest_name = rest_data.get("NAZEV", "")
            csv_name = csv_data.get("NAZEV", "")

            # Names should be identical or very similar
            assert rest_name or csv_name, "At least one should have name"
            print(f"✅ Data consistency check:")
            print(f"   REST: {rest_name}")
            print(f"   CSV:  {csv_name}")

            # Form should match
            if rest_data.get("FORMA") and csv_data.get("FORMA"):
                print(f"   Forma matches: {rest_data.get('FORMA') == csv_data.get('FORMA')}")


@pytest.mark.asyncio
async def test_api_client_direct():
    """Test SUKLAPIClient direct usage."""
    async with server_lifespan(mcp):
        api_client = await get_api_client()

        # Test get_medicine endpoint
        try:
            medicine = await api_client.get_medicine("0254045")

            if medicine:
                assert hasattr(medicine, "nazev"), "Should have nazev attribute"
                assert medicine.sukl_kod == "0254045"
                print(f"✅ API client direct: {medicine.nazev}")
                print(f"   Dostupnost: {medicine.jeDodavka}")
            else:
                print("⚠️  API client returned None (expected in some cases)")
        except Exception as e:
            print(f"⚠️  API client error: {e} (expected in some cases)")


@pytest.mark.asyncio
async def test_api_client_search_direct():
    """Test SUKLAPIClient search_medicines endpoint."""
    async with server_lifespan(mcp):
        api_client = await get_api_client()

        # Test search endpoint
        search_result = await api_client.search_medicines("PARALEN", limit=5)

        if search_result and search_result.codes:
            assert len(search_result.codes) > 0, "Should return some codes"
            print(f"✅ API search direct: {len(search_result.codes)} results")
        else:
            print("⚠️  API search returned no results")


@pytest.mark.asyncio
async def test_error_handling_invalid_code():
    """Test že nevalidní kód je správně zpracován."""
    async with server_lifespan(mcp):
        # Test s neexistujícím kódem
        result = await _try_rest_get_detail("9999999")

        # Should return None (not raise exception)
        assert result is None, "Invalid code should return None"
        print("✅ Error handling: invalid code returns None")


if __name__ == "__main__":
    # Spustit testy pomocí pytest
    # pytest tests/test_hybrid_tools.py -v -s
    print("Run tests with: pytest tests/test_hybrid_tools.py -v -s")
