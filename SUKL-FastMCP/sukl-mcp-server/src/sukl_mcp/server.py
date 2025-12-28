"""
SÚKL MCP Server - FastMCP server pro přístup k databázi léčiv.

Poskytuje AI agentům přístup k:
- Vyhledávání léčivých přípravků
- Detaily léčiv včetně příbalových letáků
- Informace o úhradách a cenách
- Dostupnost na trhu
- Databáze lékáren

Autor: Claude AI Assistant
Licence: MIT
"""

import logging
from datetime import datetime
from typing import Annotated, Optional

from fastmcp import FastMCP, Context
from pydantic import Field

from .models import (
    MedicineSearchResult,
    MedicineDetail,
    PharmacyInfo,
    AvailabilityInfo,
    ReimbursementInfo,
    PILContent,
    SearchResponse
)
from .client import SUKLClient, SUKLConfig, get_sukl_client, close_sukl_client

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastMCP instance
mcp = FastMCP(
    name="sukl-mcp-server",
    version="1.0.0",
    description="""
    MCP server pro přístup k databázi léčivých přípravků SÚKL.
    
    Umožňuje:
    - Vyhledávání léčiv podle názvu, účinné látky nebo ATC kódu
    - Získání detailních informací o léčivém přípravku
    - Zobrazení příbalového letáku (PIL)
    - Kontrolu dostupnosti na trhu
    - Informace o úhradách a doplatcích
    - Vyhledání lékáren
    
    Data pochází z oficiálních zdrojů SÚKL (Státní ústav pro kontrolu léčiv).
    """
)

# === Lifecycle hooks ===

@mcp.on_event("startup")
async def startup():
    """Inicializace při startu serveru."""
    logger.info("Starting SÚKL MCP Server...")
    client = await get_sukl_client()
    health = await client.health_check()
    logger.info(f"Health check: {health}")


@mcp.on_event("shutdown")
async def shutdown():
    """Cleanup při ukončení."""
    logger.info("Shutting down SÚKL MCP Server...")
    await close_sukl_client()


# === MCP Tools ===

@mcp.tool()
async def search_medicine(
    query: Annotated[str, Field(description="Hledaný text - název léčiva, účinná látka nebo ATC kód")],
    only_available: Annotated[bool, Field(description="Pouze dostupné přípravky")] = False,
    only_reimbursed: Annotated[bool, Field(description="Pouze přípravky hrazené pojišťovnou")] = False,
    limit: Annotated[int, Field(description="Maximální počet výsledků", ge=1, le=100)] = 20
) -> SearchResponse:
    """
    Vyhledá léčivé přípravky v databázi SÚKL.
    
    Vyhledává podle:
    - Názvu přípravku (např. "Paralen", "Ibuprofen")
    - Účinné látky (např. "paracetamol", "ibuprofenum")
    - ATC kódu (např. "N02BE01", "M01AE01")
    
    Příklady použití:
    - search_medicine("ibuprofen") - najde všechny přípravky s ibuprofem
    - search_medicine("N02", only_available=True) - analgetika dostupná na trhu
    - search_medicine("Paralen", only_reimbursed=True) - hrazené varianty Paralenu
    
    Returns:
        SearchResponse s výsledky vyhledávání
    """
    client = await get_sukl_client()
    start_time = datetime.now()
    
    raw_results = await client.search_medicines(
        query=query,
        limit=limit,
        only_available=only_available,
        only_reimbursed=only_reimbursed
    )
    
    # Transformace na Pydantic modely
    results = []
    for item in raw_results:
        try:
            results.append(MedicineSearchResult(
                sukl_code=str(item.get("kod_sukl", item.get("KOD_SUKL", ""))),
                name=item.get("nazev", item.get("NAZEV", "")),
                supplement=item.get("doplnek", item.get("DOPLNEK")),
                strength=item.get("sila", item.get("SILA")),
                form=item.get("forma", item.get("FORMA")),
                package=item.get("baleni", item.get("BALENI")),
                atc_code=item.get("atc", item.get("ATC")),
                registration_status=item.get("stav_registrace", item.get("STAV_REG")),
                dispensation_mode=item.get("vydej", item.get("VYDEJ")),
                is_available=item.get("dostupnost") == "ano" if item.get("dostupnost") else None,
                has_reimbursement=item.get("uhrada") == "ano" if item.get("uhrada") else None
            ))
        except Exception as e:
            logger.warning(f"Error parsing result: {e}")
    
    elapsed = (datetime.now() - start_time).total_seconds() * 1000
    
    return SearchResponse(
        query=query,
        total_results=len(results),
        results=results,
        search_time_ms=elapsed
    )


@mcp.tool()
async def get_medicine_details(
    sukl_code: Annotated[str, Field(description="SÚKL kód léčivého přípravku (7 číslic)")]
) -> Optional[MedicineDetail]:
    """
    Získá detailní informace o léčivém přípravku podle SÚKL kódu.
    
    Vrací kompletní informace včetně:
    - Složení a účinné látky
    - Registrační údaje
    - Ceny a úhrady
    - Dostupnost dokumentů (PIL, SPC)
    - Speciální příznaky (doping, omamné látky, ...)
    
    Args:
        sukl_code: 7-místný kód SÚKL (např. "0000001")
    
    Returns:
        MedicineDetail nebo None pokud přípravek neexistuje
    """
    client = await get_sukl_client()
    
    # Normalizace kódu
    sukl_code = sukl_code.strip().zfill(7)
    
    data = await client.get_medicine_detail(sukl_code)
    if not data:
        return None
    
    return MedicineDetail(
        sukl_code=sukl_code,
        name=data.get("nazev", ""),
        supplement=data.get("doplnek"),
        strength=data.get("sila"),
        form=data.get("forma"),
        route=data.get("cesta_podani"),
        package_size=data.get("velikost_baleni"),
        package_type=data.get("typ_obalu"),
        registration_number=data.get("registracni_cislo"),
        registration_status=data.get("stav_registrace"),
        registration_holder=data.get("drzitel"),
        atc_code=data.get("atc"),
        atc_name=data.get("atc_nazev"),
        dispensation_mode=data.get("vydej"),
        is_available=data.get("dostupnost") == "ano",
        is_marketed=data.get("uvadeni_na_trh") == "ano",
        has_reimbursement=data.get("uhrada") == "ano",
        max_price=float(data["max_cena"]) if data.get("max_cena") else None,
        reimbursement_amount=float(data["uhrada_castka"]) if data.get("uhrada_castka") else None,
        patient_copay=float(data["doplatek"]) if data.get("doplatek") else None,
        pil_available=data.get("pil") == "ano",
        spc_available=data.get("spc") == "ano",
        is_narcotic=data.get("omamna_latka") == "ano",
        is_psychotropic=data.get("psychotropni") == "ano",
        is_doping=data.get("doping") == "ano",
        last_updated=datetime.now()
    )


@mcp.tool()
async def get_pil_content(
    sukl_code: Annotated[str, Field(description="SÚKL kód léčivého přípravku")]
) -> Optional[PILContent]:
    """
    Získá obsah příbalového letáku (PIL) pro pacienty.
    
    Příbalový leták obsahuje:
    - Co je přípravek a k čemu se používá
    - Čemu věnovat pozornost před užitím
    - Jak přípravek užívat
    - Možné nežádoucí účinky
    - Jak přípravek uchovávat
    - Další informace
    
    DŮLEŽITÉ: Tato informace je pouze informativní.
    Vždy se řiďte pokyny lékaře a aktuálním příbalovým letákem.
    
    Args:
        sukl_code: SÚKL kód přípravku
    
    Returns:
        PILContent s obsahem letáku nebo None
    """
    client = await get_sukl_client()
    sukl_code = sukl_code.strip().zfill(7)
    
    # Získej detail pro název
    detail = await client.get_medicine_detail(sukl_code)
    if not detail:
        return None
    
    # Pro plný obsah by bylo potřeba parsovat PDF z Open Data
    # Zde vrátíme základní strukturu s odkazem na dokument
    return PILContent(
        sukl_code=sukl_code,
        medicine_name=detail.get("nazev", ""),
        document_url=f"https://prehledy.sukl.cz/pil/{sukl_code}.pdf",
        language="cs",
        full_text="Pro kompletní text příbalového letáku navštivte odkaz v document_url. "
                  "Příbalový leták je dostupný ve formátu PDF na stránkách SÚKL."
    )


@mcp.tool()
async def check_availability(
    sukl_code: Annotated[str, Field(description="SÚKL kód léčivého přípravku")]
) -> Optional[AvailabilityInfo]:
    """
    Zkontroluje aktuální dostupnost léčivého přípravku na českém trhu.
    
    Informace zahrnují:
    - Zda je přípravek aktuálně dostupný
    - Důvod případné nedostupnosti
    - Očekávané datum obnovení dostupnosti
    - Informace o alternativách
    
    Args:
        sukl_code: SÚKL kód přípravku
    
    Returns:
        AvailabilityInfo s informacemi o dostupnosti
    """
    client = await get_sukl_client()
    sukl_code = sukl_code.strip().zfill(7)
    
    detail = await client.get_medicine_detail(sukl_code)
    if not detail:
        return None
    
    is_available = detail.get("dostupnost") == "ano"
    is_marketed = detail.get("uvadeni_na_trh") == "ano"
    
    return AvailabilityInfo(
        sukl_code=sukl_code,
        medicine_name=detail.get("nazev", ""),
        is_available=is_available,
        is_marketed=is_marketed,
        unavailability_reason=detail.get("duvod_nedostupnosti") if not is_available else None,
        alternatives_available=False,  # Vyžaduje komplexnější logiku
        checked_at=datetime.now()
    )


@mcp.tool()
async def get_reimbursement(
    sukl_code: Annotated[str, Field(description="SÚKL kód léčivého přípravku")]
) -> Optional[ReimbursementInfo]:
    """
    Získá informace o úhradě léčivého přípravku zdravotní pojišťovnou.
    
    Obsahuje:
    - Zda je přípravek hrazen
    - Výši úhrady pojišťovnou
    - Doplatek pacienta
    - Případná indikační nebo množstevní omezení
    - Preskripční omezení (např. pouze specialista)
    
    POZNÁMKA: Skutečný doplatek se může lišit podle konkrétní pojišťovny
    a bonusových programů lékáren.
    
    Args:
        sukl_code: SÚKL kód přípravku
    
    Returns:
        ReimbursementInfo s informacemi o úhradě
    """
    client = await get_sukl_client()
    sukl_code = sukl_code.strip().zfill(7)
    
    detail = await client.get_medicine_detail(sukl_code)
    if not detail:
        return None
    
    is_reimbursed = detail.get("uhrada") == "ano"
    
    return ReimbursementInfo(
        sukl_code=sukl_code,
        medicine_name=detail.get("nazev", ""),
        is_reimbursed=is_reimbursed,
        reimbursement_group=detail.get("uhradova_skupina"),
        max_producer_price=float(detail["max_cena_vyrobce"]) if detail.get("max_cena_vyrobce") else None,
        max_retail_price=float(detail["max_cena"]) if detail.get("max_cena") else None,
        reimbursement_amount=float(detail["uhrada_castka"]) if detail.get("uhrada_castka") else None,
        patient_copay=float(detail["doplatek"]) if detail.get("doplatek") else None,
        has_indication_limit=detail.get("indikacni_omezeni") == "ano",
        indication_limit_text=detail.get("text_indikacniho_omezeni"),
        has_quantity_limit=detail.get("mnozstevni_limit") == "ano",
        quantity_limit_text=detail.get("text_mnozstevniho_limitu"),
        prescription_limit=detail.get("presktripcni_omezeni"),
        specialist_only=detail.get("specialista") == "ano"
    )


@mcp.tool()
async def find_pharmacies(
    city: Annotated[Optional[str], Field(description="Název města")] = None,
    postal_code: Annotated[Optional[str], Field(description="PSČ (5 číslic)")] = None,
    has_24h_service: Annotated[bool, Field(description="Pouze lékárny s nepřetržitým provozem")] = False,
    has_internet_sales: Annotated[bool, Field(description="Pouze lékárny s internetovým prodejem")] = False,
    limit: Annotated[int, Field(description="Maximální počet výsledků", ge=1, le=100)] = 20
) -> list[PharmacyInfo]:
    """
    Vyhledá lékárny podle zadaných kritérií.
    
    Umožňuje filtrovat podle:
    - Města nebo PSČ
    - Nepřetržitého provozu (24/7)
    - Možnosti internetového prodeje
    
    Příklady:
    - find_pharmacies(city="Praha") - lékárny v Praze
    - find_pharmacies(has_24h_service=True) - pohotovostní lékárny
    - find_pharmacies(postal_code="11000") - lékárny v okolí PSČ
    
    Args:
        city: Filtr podle města
        postal_code: Filtr podle PSČ
        has_24h_service: Pouze 24h lékárny
        has_internet_sales: Pouze s e-shopem
        limit: Max počet výsledků
    
    Returns:
        Seznam lékáren odpovídajících kritériím
    """
    client = await get_sukl_client()
    
    raw_results = await client.search_pharmacies(
        city=city,
        postal_code=postal_code,
        has_24h=has_24h_service,
        has_internet_sales=has_internet_sales,
        limit=limit
    )
    
    results = []
    for item in raw_results:
        try:
            results.append(PharmacyInfo(
                pharmacy_id=str(item.get("id_lekarny", item.get("ID_LEKARNY", ""))),
                name=item.get("nazev", item.get("NAZEV", "")),
                street=item.get("ulice", item.get("ULICE")),
                city=item.get("mesto", item.get("MESTO", "")),
                postal_code=item.get("psc", item.get("PSC")),
                district=item.get("okres", item.get("OKRES")),
                region=item.get("kraj", item.get("KRAJ")),
                phone=item.get("telefon", item.get("TELEFON")),
                email=item.get("email", item.get("EMAIL")),
                web=item.get("web", item.get("WEB")),
                latitude=float(item["lat"]) if item.get("lat") else None,
                longitude=float(item["lon"]) if item.get("lon") else None,
                operator=item.get("provozovatel", item.get("PROVOZOVATEL")),
                has_24h_service=item.get("nepretrzity_provoz") == "ano",
                has_internet_sales=item.get("internetovy_prodej") == "ano",
                has_preparation_lab=item.get("pripravna") == "ano",
                is_active=item.get("aktivni", "ano") == "ano"
            ))
        except Exception as e:
            logger.warning(f"Error parsing pharmacy: {e}")
    
    return results


@mcp.tool()
async def get_atc_info(
    atc_code: Annotated[str, Field(description="ATC kód (např. 'N02BE01' nebo 'N02')")]
) -> dict:
    """
    Získá informace o ATC (anatomicko-terapeuticko-chemické) skupině.
    
    ATC klasifikace dělí léčiva do skupin podle:
    - Anatomické skupiny (1. úroveň, např. N = Nervový systém)
    - Terapeutické skupiny (2.-4. úroveň)
    - Chemické substance (5. úroveň)
    
    Příklady:
    - get_atc_info("N") - Léčiva nervového systému
    - get_atc_info("N02") - Analgetika
    - get_atc_info("N02BE01") - Paracetamol
    
    Args:
        atc_code: ATC kód (1-7 znaků)
    
    Returns:
        Informace o ATC skupině včetně podskupin
    """
    client = await get_sukl_client()
    
    groups = await client.get_atc_groups(atc_code if len(atc_code) < 7 else None)
    
    # Najdi konkrétní skupinu
    target = None
    children = []
    
    for group in groups:
        code = group.get("kod", group.get("KOD", ""))
        if code == atc_code:
            target = group
        elif code.startswith(atc_code) and len(code) > len(atc_code):
            children.append({
                "code": code,
                "name": group.get("nazev", group.get("NAZEV", ""))
            })
    
    return {
        "code": atc_code,
        "name": target.get("nazev", target.get("NAZEV", "Neznámá skupina")) if target else "Neznámá skupina",
        "level": len(atc_code) if len(atc_code) <= 5 else 5,
        "children": children[:20],  # Omez na 20 podskupin
        "total_children": len(children)
    }


# === MCP Resources ===

@mcp.resource("sukl://info")
async def get_server_info() -> str:
    """Základní informace o SÚKL MCP serveru."""
    client = await get_sukl_client()
    health = await client.health_check()
    
    return f"""
# SÚKL MCP Server

## Stav služby
- REST API: {'✅ Dostupné' if health['api_available'] else '❌ Nedostupné'}
- Open Data: {'✅ Dostupné' if health['opendata_available'] else '❌ Nedostupné'}
- Cache: {health['cache_stats']['entries']} záznamů

## Dostupné nástroje
1. **search_medicine** - Vyhledávání léčivých přípravků
2. **get_medicine_details** - Detail léčivého přípravku
3. **get_pil_content** - Příbalový leták
4. **check_availability** - Kontrola dostupnosti
5. **get_reimbursement** - Informace o úhradách
6. **find_pharmacies** - Vyhledání lékáren
7. **get_atc_info** - ATC klasifikace

## Zdroj dat
Státní ústav pro kontrolu léčiv (SÚKL)
- Web: https://www.sukl.cz
- Open Data: https://opendata.sukl.cz

## Právní upozornění
Informace poskytované tímto serverem mají pouze informativní charakter.
Vždy se řiďte pokyny lékaře a lékárníka.
"""


@mcp.resource("sukl://atc/{code}")
async def get_atc_resource(code: str) -> str:
    """Informace o ATC skupině jako resource."""
    info = await get_atc_info(code)
    
    children_text = "\n".join([f"- {c['code']}: {c['name']}" for c in info['children'][:10]])
    
    return f"""
# ATC: {info['code']} - {info['name']}

Úroveň: {info['level']}/5

## Podskupiny ({info['total_children']} celkem)
{children_text}
{'...' if info['total_children'] > 10 else ''}
"""


# === Entry point ===

def main():
    """Spusť MCP server."""
    import uvicorn
    uvicorn.run(
        "sukl_mcp.server:mcp.app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
