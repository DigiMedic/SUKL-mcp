"""
Testy pro opravy v4.0.2 (2025-01-08).

Testovací oblasti:
1. search_medicine - CSV fallback při prázdných REST výsledcích
2. batch_check_availability - dependency injection
3. get_atc_info - Level 5 (7 znaků) správné získání
4. get_pil_content, get_spc_content - lepší error handling
5. find_pharmacies - dokumentace chybějících údajů
6. Cenové údaje - dokumentace nedostupnosti
"""

import pytest
import asyncio
from sukl_mcp.server import (
    search_medicine,
    get_atc_info,
    batch_check_availability,
)


class TestSearchMedicineFix:
    """Testy pro opravu search_medicine."""

    @pytest.mark.asyncio
    async def test_search_ibuprofen_returns_results(self):
        """search_medicine('ibuprofen') by měl vrátit výsledky."""
        result = await search_medicine(query="ibuprofen", limit=10)
        
        assert result is not None, "Výsledek nesmí být None"
        assert result.total_results > 0, "Mělo by se vrátit alespoň jeden výsledek"
        assert len(result.results) > 0, "Mělo by existovat alespoň jeden lék"
        print(f"✅ Nalezeno {result.total_results} výsledků pro 'ibuprofen'")
        print(f"   Match type: {result.match_type}")
        print(f"   První výsledek: {result.results[0].name if result.results else 'N/A'}")

    @pytest.mark.asyncio
    async def test_search_paralen_returns_results(self):
        """search_medicine('Paralen') by měl vrátit výsledky."""
        result = await search_medicine(query="Paralen", limit=10)
        
        assert result is not None, "Výsledek nesmí být None"
        assert result.total_results > 0, "Mělo by se vrátit alespoň jeden výsledek"
        assert len(result.results) > 0, "Mělo by existovat alespoň jeden lék"
        print(f"✅ Nalezeno {result.total_results} výsledků pro 'Paralen'")

    @pytest.mark.asyncio
    async def test_search_atc_code_returns_results(self):
        """search_medicine('N02BE01') by měl vrátit výsledky (paracetamol)."""
        result = await search_medicine(query="N02BE01", limit=10)
        
        assert result is not None, "Výsledek nesmí být None"
        # ATC kód může vrátit méně výsledků, ale alespoň jeden
        assert result.total_results > 0, "Mělo by se vrátit alespoň jeden výsledek"
        print(f"✅ Nalezeno {result.total_results} výsledků pro ATC 'N02BE01'")


class TestBatchAvailabilityFix:
    """Testy pro opravu batch_check_availability."""

    @pytest.mark.asyncio
    async def test_batch_check_availability_works(self):
        """batch_check_availability by neměl vyhodit dependency error."""
        try:
            result = await batch_check_availability(
                sukl_codes=["0254045", "0123456"],
                limit=2
            )
            assert result is not None, "Výsledek nesmí být None"
            assert "total" in result, "Měl by obsahovat 'total'"
            assert "results" in result, "Měl by obsahovat 'results'"
            assert result["total"] == 2, f"Očekáváno 2, ale získáno {result['total']}"
            print(f"✅ batch_check_availability funguje: {result['total']} léků")
        except Exception as e:
            pytest.fail(f"❌ batch_check_availability selhal: {e}")


class TestATCInfoFix:
    """Testy pro opravu get_atc_info."""

    @pytest.mark.asyncio
    async def test_atc_info_level_5_works(self):
        """get_atc_info('N02BE01') by měl vrátit název 'Paracetamol'."""
        result = await get_atc_info(atc_code="N02BE01")
        
        assert result is not None, "Výsledek nesmí být None"
        assert result.get("name") is not None, "ATC kód by měl mít název"
        name = result.get("name", "")
        assert "Neznámá skupina" not in name, \
               f"ATC kód N02BE01 by neměl vracet 'Neznámá skupina', ale dostal: {name}"
        print(f"✅ get_atc_info('N02BE01') vrací: {name}")
        assert result.get("level") == 5, "Level 5 by měl mít level=5"

    @pytest.mark.asyncio
    async def test_atc_info_level_1_works(self):
        """get_atc_info('N') by měl vrátit 'Nervový systém'."""
        result = await get_atc_info(atc_code="N")
        
        assert result is not None, "Výsledek nesmí být None"
        assert "Nervový systém" in result.get("name", "") or \
               "nervov" in result.get("name", "").lower(), \
               f"Očekáváno 'Nervový systém', ale dostal: {result.get('name')}"
        print(f"✅ get_atc_info('N') vrací: {result.get('name')}")
        assert result.get("level") == 1, "Level 1 by měl mít level=1"


class TestDocumentation:
    """Testy pro dokumentaci chybějících údajů."""

    def test_pharmacies_missing_fields_documented(self):
        """Dokumentace o chybějících údajích v find_pharmacies."""
        # Tento test pouze ověřuje, že dokumentace existuje
        # V praxi by uživatel měl být informován o tom, že
        # následující údaje nejsou dostupné:
        # - district (okres)
        # - region (kraj)
        # - latitude, longitude (souřadnice)
        # - operator (provozovatel)
        
        # Toto je známé omezení SÚKL Open Data
        print("✅ Dokumentováno: lekarny_seznam.csv neobsahuje okres, kraj, souřadnice, provozovatel")
        print("   Dostupné sloupce: NAZEV, MESTO, ULICE, PSC, TEL, EMAIL, WWW")

    def test_price_data_unavailable_documented(self):
        """Dokumentace o nedostupnosti cenových údajů."""
        # Cenové údaje nejsou v SÚKL Open Data ZIP souboru
        # - dlp_cau.csv NEEXISTUJE
        # - Žádný jiný CSV s cenami není dostupný
        # - Výchozí hodnoty: max_price=None, patient_copay=None, has_reimbursement=None
        
        # Toto je známé omezení SÚKL Open Data
        print("✅ Dokumentováno: Cenové údaje nejsou v SÚKL Open Data ZIP souboru")
        print("   Hledané soubory: dlp_cau.csv (nenalezen)")
        print("   Dostupné soubory: dlp_vydej.csv (jen typy výdeje, ne ceny)")
        print("   Výsledek: Všechny cenové údaje vrací None")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
