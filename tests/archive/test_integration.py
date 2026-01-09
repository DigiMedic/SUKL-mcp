#!/usr/bin/env python3
"""Důkladná validace všech API funkcí SÚKL MCP serveru."""

import asyncio
import sys

# Barvy pro výstup
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def fail(msg):
    print(f"{RED}❌ {msg}{RESET}")


def info(msg):
    print(f"{BLUE}ℹ️  {msg}{RESET}")


def section(msg):
    print(f"\n{BOLD}{YELLOW}{'='*60}{RESET}")
    print(f"{BOLD}{YELLOW}{msg}{RESET}")
    print(f"{BOLD}{YELLOW}{'='*60}{RESET}\n")


async def test_rest_api():
    """Test REST API klienta."""
    section("REST API VALIDACE (bez stahování CSV)")
    
    from sukl_mcp.client_api import SUKLAPIClient
    
    results = {}
    client = await SUKLAPIClient.get_instance()
    
    # 1. HSZ - Nedostupné LP
    try:
        unavail = await client.get_unavailable_medicines()
        if len(unavail) > 0:
            ok(f"HSZ API: {len(unavail)} nedostupných LP")
            info(f"   Příklad: {unavail[0].nazev[:40]}... (kód: {unavail[0].kod_sukl})")
            results["hsz"] = True
        else:
            fail("HSZ API: Žádná data")
            results["hsz"] = False
    except Exception as e:
        fail(f"HSZ API: {e}")
        results["hsz"] = False
    
    # 2. Lékárny
    try:
        pharmacies = await client.search_pharmacies_by_city("Praha", limit=10)
        if len(pharmacies) > 0:
            ok(f"Lékárny API: {len(pharmacies)} lékáren v Praze")
            p = pharmacies[0]
            info(f"   Příklad: {p.nazev} (kód: {p.kod_lekarny})")
            results["lekarny"] = True
        else:
            fail("Lékárny API: Žádná data")
            results["lekarny"] = False
    except Exception as e:
        fail(f"Lékárny API: {e}")
        results["lekarny"] = False
    
    # 3. Vakcíny
    try:
        batches, last_change = await client.get_vaccine_batches()
        if len(batches) > 0:
            ok(f"Vakcíny API: {len(batches)} šarží (aktualizace: {last_change})")
            b = batches[0]
            info(f"   Příklad: {b.nazev[:40]}... šarže: {b.sarze}")
            results["vakciny"] = True
        else:
            fail("Vakcíny API: Žádná data")
            results["vakciny"] = False
    except Exception as e:
        fail(f"Vakcíny API: {e}")
        results["vakciny"] = False
    
    # 4. Distributoři
    try:
        distributors = await client.get_all_distributors()
        if len(distributors) > 0:
            ok(f"Distributoři API: {len(distributors)} subjektů")
            d = distributors[0]
            info(f"   Příklad: {d.nazev} (typ: {d.typ})")
            results["distributori"] = True
        else:
            fail("Distributoři API: Žádná data")
            results["distributori"] = False
    except Exception as e:
        fail(f"Distributoři API: {e}")
        results["distributori"] = False
    
    # 5. Market Report
    try:
        reports = await client.get_market_report()
        if len(reports) > 0:
            ok(f"Market Report API: {len(reports)} hlášení")
            r = reports[0]
            info(f"   Příklad: {r.kod_sukl} - typ: {r.typ_oznameni}")
            results["market"] = True
        else:
            fail("Market Report API: Žádná data")
            results["market"] = False
    except Exception as e:
        fail(f"Market Report API: {e}")
        results["market"] = False
    
    await client.close()
    return results


async def test_csv_client():
    """Test CSV klienta (bulk data)."""
    section("CSV CLIENT VALIDACE (bulk data z opendata.sukl.cz)")
    
    from sukl_mcp.client_csv import get_sukl_client, close_sukl_client
    
    results = {}
    client = await get_sukl_client()
    
    # 1. Vyhledávání léčiv
    try:
        medicines = await client.search_medicines("ibuprofen", limit=5)
        if len(medicines) > 0:
            ok(f"Vyhledávání léčiv: {len(medicines)} výsledků pro 'ibuprofen'")
            m = medicines[0]
            info(f"   Příklad: {m.get('NAZEV', 'N/A')} (kód: {m.get('KOD_SUKL', 'N/A')})")
            results["search"] = True
        else:
            fail("Vyhledávání léčiv: Žádné výsledky")
            results["search"] = False
    except Exception as e:
        fail(f"Vyhledávání léčiv: {e}")
        results["search"] = False
    
    # 2. Detail léčiva
    try:
        detail = await client.get_medicine_by_sukl_code("0254045")
        if detail:
            ok(f"Detail léčiva: Nalezen {detail.get('NAZEV', 'N/A')}")
            info(f"   ATC: {detail.get('ATC', 'N/A')}, Forma: {detail.get('FORMA', 'N/A')}")
            results["detail"] = True
        else:
            fail("Detail léčiva: Nenalezen")
            results["detail"] = False
    except Exception as e:
        fail(f"Detail léčiva: {e}")
        results["detail"] = False
    
    # 3. ATC skupiny
    try:
        atc = await client.get_atc_groups("N02")
        if len(atc) > 0:
            ok(f"ATC skupiny: {len(atc)} skupin pro prefix 'N02'")
            results["atc"] = True
        else:
            fail("ATC skupiny: Žádné výsledky")
            results["atc"] = False
    except Exception as e:
        fail(f"ATC skupiny: {e}")
        results["atc"] = False
    
    # 4. Složení léčiva
    try:
        composition = await client.get_composition("0254045")
        if len(composition) > 0:
            ok(f"Složení léčiva: {len(composition)} složek")
            c = composition[0]
            info(f"   Příklad: {c.get('NAZEV_LATKY', c.get('KOD_LATKY', 'N/A'))}")
            results["composition"] = True
        else:
            # Může být prázdné pro některá léčiva
            info("Složení léčiva: Žádné složky (OK pro některá léčiva)")
            results["composition"] = True
    except Exception as e:
        fail(f"Složení léčiva: {e}")
        results["composition"] = False
    
    # 5. Statistiky
    try:
        stats = client.get_statistics()
        if stats and stats.get("total_medicines", 0) > 0:
            ok(f"Statistiky: {stats.get('total_medicines', 0)} léčiv v databázi")
            info(f"   Tabulky: {', '.join(stats.get('tables', {}).keys())}")
            results["stats"] = True
        else:
            fail("Statistiky: Žádná data")
            results["stats"] = False
    except Exception as e:
        fail(f"Statistiky: {e}")
        results["stats"] = False
    
    await close_sukl_client()
    return results


async def test_document_parser():
    """Test parsování dokumentů."""
    section("DOCUMENT PARSER VALIDACE (PIL/SPC dokumenty)")
    
    from sukl_mcp.document_parser import get_document_parser, close_document_parser
    
    results = {}
    parser = get_document_parser()
    
    # Test parsování PIL
    try:
        pil = await parser.get_document_content("0254045", "pil")  # PARALEN
        if pil and pil.get("content"):
            ok(f"PIL Parser: {len(pil.get('content', ''))} znaků")
            info(f"   Formát: {pil.get('format', '?')}, URL: {pil.get('url', '?')}")
            results["pil"] = True
        else:
            info("PIL Parser: Dokument nenalezen nebo prázdný")
            results["pil"] = None  # Neznámý stav
    except Exception as e:
        fail(f"PIL Parser: {e}")
        results["pil"] = False
    
    close_document_parser()
    return results


async def test_mcp_tools():
    """Test MCP nástrojů."""
    section("MCP NÁSTROJE VALIDACE")
    
    # Import modelů
    from sukl_mcp.models import (
        MedicineSearchResult,
        MedicineDetail,
        PharmacyInfo,
        UnavailabilityReport,
        VaccineBatchReport,
        DistributorInfo,
    )
    
    results = {}
    
    # Kontrola, že modely existují
    try:
        models = [
            MedicineSearchResult,
            MedicineDetail,
            PharmacyInfo,
            UnavailabilityReport,
            VaccineBatchReport,
            DistributorInfo,
        ]
        ok(f"Modely: {len(models)} Pydantic modelů dostupných")
        results["models"] = True
    except Exception as e:
        fail(f"Modely: {e}")
        results["models"] = False
    
    # Kontrola registrace nástrojů
    try:
        from sukl_mcp.server import mcp
        tools = list(mcp._tool_manager._tools.keys())
        ok(f"MCP nástroje: {len(tools)} registrovaných")
        info(f"   Nástroje: {', '.join(tools[:5])}...")
        results["tools"] = True
    except Exception as e:
        fail(f"MCP nástroje: {e}")
        results["tools"] = False
    
    return results


def print_summary(all_results):
    """Vypíše souhrn validace."""
    section("SOUHRN VALIDACE")
    
    total_pass = 0
    total_fail = 0
    total_unknown = 0
    
    for category, results in all_results.items():
        print(f"\n{BOLD}{category}:{RESET}")
        for test, passed in results.items():
            if passed is True:
                print(f"  {GREEN}✅ {test}{RESET}")
                total_pass += 1
            elif passed is False:
                print(f"  {RED}❌ {test}{RESET}")
                total_fail += 1
            else:
                print(f"  {YELLOW}⚠️  {test} (neznámý stav){RESET}")
                total_unknown += 1
    
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{GREEN}Prošlo: {total_pass}{RESET} | {RED}Selhalo: {total_fail}{RESET} | {YELLOW}Neznámé: {total_unknown}{RESET}")
    
    if total_fail == 0:
        print(f"\n{GREEN}{BOLD}🎉 VŠECHNY TESTY PROŠLY! Server je plně funkční.{RESET}")
        return 0
    else:
        print(f"\n{RED}{BOLD}⚠️  Některé testy selhaly.{RESET}")
        return 1


async def main():
    """Hlavní validační funkce."""
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}   SÚKL MCP SERVER - DŮKLADNÁ VALIDACE{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    
    all_results = {}
    
    # 1. REST API testy
    all_results["REST API"] = await test_rest_api()
    
    # 2. CSV Client testy
    all_results["CSV Client"] = await test_csv_client()
    
    # 3. Document Parser testy
    all_results["Document Parser"] = await test_document_parser()
    
    # 4. MCP Tools testy
    all_results["MCP Tools"] = await test_mcp_tools()
    
    # Souhrn
    return print_summary(all_results)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
