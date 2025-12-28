"""
SÚKL MCP Server - FastMCP server pro přístup k databázi léčiv.

Poskytuje AI agentům přístup k české databázi léčivých přípravků.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastmcp import FastMCP

from .client_csv import close_sukl_client, get_sukl_client
from .models import (
    AvailabilityInfo,
    MedicineDetail,
    MedicineSearchResult,
    PILContent,
    PharmacyInfo,
    ReimbursementInfo,
    SearchResponse,
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# === Lifecycle management ===


@asynccontextmanager
async def server_lifespan(server):
    """Inicializace a cleanup serveru."""
    logger.info("Starting SÚKL MCP Server...")
    client = await get_sukl_client()
    health = await client.health_check()
    logger.info(f"Health check: {health}")

    yield

    logger.info("Shutting down SÚKL MCP Server...")
    await close_sukl_client()


# === FastMCP instance ===

mcp = FastMCP(
    name="SÚKL MCP Server",
    version="1.0.0",
    lifespan=server_lifespan,
    instructions="""
    Tento MCP server poskytuje přístup k databázi léčivých přípravků SÚKL.

    Umožňuje:
    - Vyhledávání léčiv podle názvu, účinné látky nebo ATC kódu
    - Získání detailních informací o léčivém přípravku
    - Zobrazení příbalového letáku (PIL)
    - Kontrolu dostupnosti na trhu
    - Informace o úhradách a doplatcích
    - Vyhledání lékáren

    Data pochází z oficiálních zdrojů SÚKL (Státní ústav pro kontrolu léčiv).
    """,
)


# === MCP Tools ===


@mcp.tool
async def search_medicine(
    query: str,
    only_available: bool = False,
    only_reimbursed: bool = False,
    limit: int = 20,
) -> SearchResponse:
    """
    Vyhledá léčivé přípravky v databázi SÚKL.

    Vyhledává podle názvu přípravku, účinné látky nebo ATC kódu.

    Args:
        query: Hledaný text - název léčiva, účinná látka nebo ATC kód
        only_available: Pouze dostupné přípravky na trhu
        only_reimbursed: Pouze přípravky hrazené pojišťovnou
        limit: Maximální počet výsledků (1-100)

    Returns:
        SearchResponse s výsledky vyhledávání

    Examples:
        - search_medicine("ibuprofen")
        - search_medicine("N02", only_available=True)
        - search_medicine("Paralen", only_reimbursed=True)
    """
    client = await get_sukl_client()
    start_time = datetime.now()

    raw_results = await client.search_medicines(
        query=query, limit=limit, only_available=only_available, only_reimbursed=only_reimbursed
    )

    # Transformace na Pydantic modely
    results = []
    for item in raw_results:
        try:
            results.append(
                MedicineSearchResult(
                    sukl_code=str(item.get("kod_sukl", item.get("KOD_SUKL", ""))),
                    name=item.get("nazev", item.get("NAZEV", "")),
                    supplement=item.get("doplnek", item.get("DOPLNEK")),
                    strength=item.get("sila", item.get("SILA")),
                    form=item.get("forma", item.get("FORMA")),
                    package=item.get("baleni", item.get("BALENI")),
                    atc_code=item.get("atc", item.get("ATC")),
                    registration_status=item.get("stav_registrace", item.get("STAV_REG")),
                    dispensation_mode=item.get("vydej", item.get("VYDEJ")),
                    is_available=item.get("dostupnost") == "ano"
                    if item.get("dostupnost")
                    else None,
                    has_reimbursement=item.get("uhrada") == "ano"
                    if item.get("uhrada")
                    else None,
                )
            )
        except Exception as e:
            logger.warning(f"Error parsing result: {e}")

    elapsed = (datetime.now() - start_time).total_seconds() * 1000

    return SearchResponse(
        query=query, total_results=len(results), results=results, search_time_ms=elapsed
    )


@mcp.tool
async def get_medicine_details(sukl_code: str) -> MedicineDetail | None:
    """
    Získá detailní informace o léčivém přípravku podle SÚKL kódu.

    Vrací kompletní informace včetně složení, registrace, cen, úhrad a dokumentů.

    Args:
        sukl_code: SÚKL kód léčivého přípravku (7 číslic, např. "0012345")

    Returns:
        MedicineDetail nebo None pokud přípravek neexistuje

    Examples:
        - get_medicine_details("0012345")
    """
    client = await get_sukl_client()

    # Normalizace kódu
    sukl_code = sukl_code.strip().zfill(7)

    data = await client.get_medicine_detail(sukl_code)
    if not data:
        return None

    # Helper pro získání hodnoty z CSV dat (velká písmena)
    def get_val(key_upper: str, default=None):
        """Získej hodnotu, podporuje jak velká tak malá písmena."""
        return data.get(key_upper, data.get(key_upper.lower(), default))

    return MedicineDetail(
        sukl_code=sukl_code,
        name=get_val("NAZEV", ""),
        supplement=get_val("DOPLNEK"),
        strength=get_val("SILA"),
        form=get_val("FORMA"),
        route=get_val("CESTA"),
        package_size=get_val("BALENI"),
        package_type=get_val("OBAL"),
        registration_number=get_val("RC"),
        registration_status=get_val("REG"),
        registration_holder=get_val("DRZ"),
        atc_code=get_val("ATC_WHO"),
        atc_name=None,  # Není v základních datech
        dispensation_mode=get_val("VYDEJ"),
        is_available=get_val("DODAVKY") != "0",
        is_marketed=True,  # Pokud je v databázi, je registrován
        has_reimbursement=False,  # TODO: získat z separátní tabulky úhrad
        max_price=None,  # TODO: získat z tabulky cen
        reimbursement_amount=None,
        patient_copay=None,
        pil_available=False,  # TODO: zkontrolovat v nazvydokumentu
        spc_available=False,
        is_narcotic=get_val("ZAV") is not None and str(get_val("ZAV")) != "nan",
        is_psychotropic=False,
        is_doping=get_val("DOPING") is not None and str(get_val("DOPING")) != "nan",
        last_updated=datetime.now(),
    )


@mcp.tool
async def get_pil_content(sukl_code: str) -> PILContent | None:
    """
    Získá obsah příbalového letáku (PIL) pro pacienty.

    Příbalový leták obsahuje informace o použití, dávkování a nežádoucích účincích.

    DŮLEŽITÉ: Tato informace je pouze informativní. Vždy se řiďte pokyny lékaře.

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

    return PILContent(
        sukl_code=sukl_code,
        medicine_name=detail.get("NAZEV", detail.get("nazev", "")),
        document_url=f"https://prehledy.sukl.cz/pil/{sukl_code}.pdf",
        language="cs",
        full_text="Pro kompletní text příbalového letáku navštivte odkaz v document_url. "
        "Příbalový leták je dostupný ve formátu PDF na stránkách SÚKL.",
    )


@mcp.tool
async def check_availability(sukl_code: str) -> AvailabilityInfo | None:
    """
    Zkontroluje aktuální dostupnost léčivého přípravku na českém trhu.

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

    # Dostupnost podle sloupce DODAVKY (0 = nedostupný)
    is_available = detail.get("DODAVKY") != "0"
    is_marketed = True  # Pokud je v databázi, je registrován

    return AvailabilityInfo(
        sukl_code=sukl_code,
        medicine_name=detail.get("NAZEV", ""),
        is_available=is_available,
        is_marketed=is_marketed,
        unavailability_reason="Přípravek není aktuálně dodáván" if not is_available else None,
        alternatives_available=False,
        checked_at=datetime.now(),
    )


@mcp.tool
async def get_reimbursement(sukl_code: str) -> ReimbursementInfo | None:
    """
    Získá informace o úhradě léčivého přípravku zdravotní pojišťovnou.

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
        max_producer_price=float(detail["max_cena_vyrobce"])
        if detail.get("max_cena_vyrobce")
        else None,
        max_retail_price=float(detail["max_cena"]) if detail.get("max_cena") else None,
        reimbursement_amount=float(detail["uhrada_castka"]) if detail.get("uhrada_castka") else None,
        patient_copay=float(detail["doplatek"]) if detail.get("doplatek") else None,
        has_indication_limit=detail.get("indikacni_omezeni") == "ano",
        indication_limit_text=detail.get("text_indikacniho_omezeni"),
        specialist_only=detail.get("specialista") == "ano",
    )


@mcp.tool
async def find_pharmacies(
    city: str | None = None,
    postal_code: str | None = None,
    has_24h_service: bool = False,
    has_internet_sales: bool = False,
    limit: int = 20,
) -> list[PharmacyInfo]:
    """
    Vyhledá lékárny podle zadaných kritérií.

    Args:
        city: Název města (volitelné)
        postal_code: PSČ (5 číslic, volitelné)
        has_24h_service: Pouze lékárny s nepřetržitým provozem
        has_internet_sales: Pouze lékárny s internetovým prodejem
        limit: Maximální počet výsledků (1-100)

    Returns:
        Seznam lékáren odpovídajících kritériím

    Examples:
        - find_pharmacies(city="Praha")
        - find_pharmacies(has_24h_service=True)
        - find_pharmacies(postal_code="11000")
    """
    client = await get_sukl_client()

    raw_results = await client.search_pharmacies(
        city=city,
        postal_code=postal_code,
        has_24h=has_24h_service,
        has_internet_sales=has_internet_sales,
        limit=limit,
    )

    results = []
    for item in raw_results:
        try:
            results.append(
                PharmacyInfo(
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
                    is_active=item.get("aktivni", "ano") == "ano",
                )
            )
        except Exception as e:
            logger.warning(f"Error parsing pharmacy: {e}")

    return results


@mcp.tool
async def get_atc_info(atc_code: str) -> dict:
    """
    Získá informace o ATC (anatomicko-terapeuticko-chemické) skupině.

    ATC klasifikace dělí léčiva do skupin podle anatomické skupiny,
    terapeutické skupiny a chemické substance.

    Args:
        atc_code: ATC kód (1-7 znaků, např. 'N', 'N02', 'N02BE01')

    Returns:
        Informace o ATC skupině včetně podskupin

    Examples:
        - get_atc_info("N") - Léčiva nervového systému
        - get_atc_info("N02") - Analgetika
        - get_atc_info("N02BE01") - Paracetamol
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
            children.append({"code": code, "name": group.get("nazev", group.get("NAZEV", ""))})

    return {
        "code": atc_code,
        "name": target.get("nazev", target.get("NAZEV", "Neznámá skupina"))
        if target
        else "Neznámá skupina",
        "level": len(atc_code) if len(atc_code) <= 5 else 5,
        "children": children[:20],
        "total_children": len(children),
    }


# === Entry point ===


def main():
    """Spusť MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
