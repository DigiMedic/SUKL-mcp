"""
SÚKL MCP Server - FastMCP server pro přístup k databázi léčiv.

Poskytuje AI agentům přístup k české databázi léčivých přípravků.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from fastmcp import Context, FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from fastmcp.server.middleware.timing import TimingMiddleware

from sukl_mcp.client_api import SUKLAPIClient, pharmacy_api_to_info

# Absolutní importy pro FastMCP Cloud compatibility
from sukl_mcp.client_csv import SUKLClient, close_sukl_client, get_sukl_client
from sukl_mcp.document_parser import close_document_parser, get_document_parser
from sukl_mcp.exceptions import SUKLDocumentError, SUKLParseError
from sukl_mcp.models import (
    AlternativeMedicine,
    ATCChild,
    ATCInfo,
    AvailabilityInfo,
    AvailabilityStatus,
    DistributorInfo,
    MarketNotificationType,
    MarketReportInfo,
    MedicineDetail,
    MedicineSearchResult,
    PharmacyInfo,
    PILContent,
    ReimbursementInfo,
    SearchResponse,
    UnavailabilityReport,
    UnavailabilityType,
    UnavailableMedicineInfo,
    VaccineBatchInfo,
    VaccineBatchReport,
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# === Application Context (Best Practice) ===


@dataclass
class AppContext:
    """Typovaný aplikační kontext pro lifespan."""

    client: "SUKLClient"  # Forward reference
    initialized_at: datetime


# === Lifecycle management ===


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncGenerator[AppContext, None]:
    """Inicializace a cleanup serveru s typovaným kontextem."""
    logger.info("Starting SÚKL MCP Server...")
    client = await get_sukl_client()

    # Explicitní inicializace při startu (Cold Start fix)
    # Stáhne a načte data do paměti, aby první request nebyl pomalý
    await client.initialize()

    health = await client.health_check()
    logger.info(f"Health check: {health}")

    # Vrať typovaný kontext
    yield AppContext(client=client, initialized_at=datetime.now())

    logger.info("Shutting down SÚKL MCP Server...")
    await close_sukl_client()
    close_document_parser()


# === FastMCP instance ===

mcp = FastMCP(
    name="SÚKL MCP Server",
    version="3.1.0",
    website_url="https://github.com/DigiMedic/SUKL-mcp",
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

# === Middleware Stack (Best Practice) ===
# Pořadí je důležité: ErrorHandling -> RateLimiting -> Timing -> Logging
mcp.add_middleware(ErrorHandlingMiddleware())  # Zachytí a zpracuje chyby
mcp.add_middleware(RateLimitingMiddleware(max_requests_per_second=50))  # Rate limiting
mcp.add_middleware(TimingMiddleware())  # Měření doby zpracování
mcp.add_middleware(LoggingMiddleware())  # Logování requestů


# === MCP Prompts (Best Practice) ===
# Předdefinované šablony pro běžné dotazy


@mcp.prompt(
    tags={"alternatives", "search", "patient"},
    title="Hledání alternativy k léčivu",
)
def find_alternative_prompt(medicine_name: str) -> str:
    """
    Vytvoří dotaz pro nalezení alternativy k léčivu.

    Použijte, když pacient hledá levnější nebo dostupnou alternativu.
    """
    return f"""Najdi dostupnou alternativu pro léčivo "{medicine_name}".

Požadavky:
1. Stejná nebo podobná účinná látka
2. Dostupné na trhu (DODAVKY = A)
3. Pokud možno s nižším doplatkem

Použij nástroj search_medicine pro vyhledání a check_availability pro ověření dostupnosti."""


@mcp.prompt(
    tags={"info", "detail", "overview"},
    title="Kompletní informace o léčivu",
)
def check_medicine_info_prompt(medicine_name: str) -> str:
    """
    Vytvoří dotaz pro získání kompletních informací o léčivu.

    Použijte pro komplexní přehled včetně ceny a dostupnosti.
    """
    return f"""Získej kompletní informace o léčivu "{medicine_name}".

Zjisti:
1. Základní informace (síla, forma, balení)
2. Dostupnost na trhu
3. Cenu a úhradu pojišťovny
4. Režim výdeje (na předpis / volně prodejné)

Použij nástroje search_medicine, get_medicine_details a get_reimbursement."""


@mcp.prompt(
    tags={"comparison", "analysis", "pricing"},
    title="Porovnání dvou léčiv",
)
def compare_medicines_prompt(medicine1: str, medicine2: str) -> str:
    """
    Vytvoří dotaz pro porovnání dvou léčiv.

    Použijte pro srovnání ceny, účinnosti nebo dostupnosti.
    """
    return f"""Porovnej léčiva "{medicine1}" a "{medicine2}".

Srovnej:
1. Účinné látky
2. Ceny a doplatky
3. Dostupnost na trhu
4. Lékové formy a síly

Použij search_medicine pro oba léky a get_reimbursement pro cenové údaje."""


# === MCP Tools ===


@mcp.tool(
    tags={"search", "medicines"},
    annotations={"readOnlyHint": True, "openWorldHint": True, "idempotentHint": True},
)
async def search_medicine(
    query: str,
    only_available: bool = False,
    only_reimbursed: bool = False,
    limit: int = 20,
    use_fuzzy: bool = True,
    ctx: Context | None = None,
) -> SearchResponse:
    """
    Vyhledá léčivé přípravky v databázi SÚKL s multi-level search pipeline.

    Vyhledává podle názvu přípravku, účinné látky nebo ATC kódu s fuzzy matchingem.

    Multi-level pipeline:
    1. Vyhledávání v účinné látce (dlp_slozeni)
    2. Exact match v názvu
    3. Substring match v názvu
    4. Fuzzy fallback (rapidfuzz, threshold 80)

    Args:
        query: Hledaný text - název léčiva, účinná látka nebo ATC kód
        only_available: Pouze dostupné přípravky na trhu
        only_reimbursed: Pouze přípravky hrazené pojišťovnou
        limit: Maximální počet výsledků (1-100)
        use_fuzzy: Použít fuzzy matching (default: True)

    Returns:
        SearchResponse s výsledky vyhledávání včetně match metadat

    Examples:
        - search_medicine("ibuprofen")
        - search_medicine("N02", only_available=True)
        - search_medicine("Paralen", only_reimbursed=True)
        - search_medicine("ibuprofn", use_fuzzy=True)  # Oprava překlepu
    """
    if ctx:
        await ctx.info(f"Vyhledávám léčiva: '{query}'")

    client = await get_sukl_client()
    start_time = datetime.now()

    # Získej výsledky s match metadaty (tuple: results, match_type)
    raw_results, match_type = await client.search_medicines(
        query=query,
        limit=limit,
        only_available=only_available,
        only_reimbursed=only_reimbursed,
        use_fuzzy=use_fuzzy,
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
                    is_available=(
                        item.get("dostupnost") == "ano" if item.get("dostupnost") else None
                    ),
                    # Cenové údaje (EPIC 3: Price & Reimbursement)
                    has_reimbursement=item.get("has_reimbursement"),
                    max_price=item.get("max_price"),
                    patient_copay=item.get("patient_copay"),
                    # Match metadata (EPIC 2: Smart Search)
                    match_score=item.get("match_score"),
                    match_type=item.get("match_type"),
                )
            )
        except Exception as e:
            logger.warning(f"Error parsing result: {e}")

    elapsed = (datetime.now() - start_time).total_seconds() * 1000

    return SearchResponse(
        query=query,
        total_results=len(results),
        results=results,
        search_time_ms=elapsed,
        match_type=match_type,
    )


@mcp.tool(
    tags={"detail", "medicines"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_medicine_details(sukl_code: str, ctx: Context | None = None) -> MedicineDetail | None:
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
    if ctx:
        await ctx.info(f"Načítám detail léčiva: {sukl_code}")

    client = await get_sukl_client()

    # Normalizace kódu
    sukl_code = sukl_code.strip().zfill(7)

    data = await client.get_medicine_detail(sukl_code)
    if not data:
        return None

    # Helper pro získání hodnoty z CSV dat (velká písmena)
    def get_val(key_upper: str, default: str | None = None) -> str | None:
        """Získej hodnotu, podporuje jak velká tal malá písmena."""
        return data.get(key_upper, data.get(key_upper.lower(), default))

    # Získej cenové údaje z dlp_cau (EPIC 3)
    price_info = await client.get_price_info(sukl_code)

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
        # Cenové údaje z dlp_cau (EPIC 3)
        has_reimbursement=price_info.get("is_reimbursed", False) if price_info else False,
        max_price=price_info.get("max_price") if price_info else None,
        reimbursement_amount=price_info.get("reimbursement_amount") if price_info else None,
        patient_copay=price_info.get("patient_copay") if price_info else None,
        pil_available=False,  # TODO: zkontrolovat v nazvydokumentu
        spc_available=False,
        is_narcotic=get_val("ZAV") is not None and str(get_val("ZAV")) != "nan",
        is_psychotropic=False,
        is_doping=get_val("DOPING") is not None and str(get_val("DOPING")) != "nan",
        last_updated=datetime.now(),
    )


@mcp.tool(
    tags={"documents", "pil"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_pil_content(sukl_code: str, ctx: Context | None = None) -> PILContent | None:
    """
    Získá obsah příbalového letáku (PIL) pro pacienty.

    Příbalový leták obsahuje informace o použití, dávkování a nežádoucích účincích.
    Dokument je automaticky stažen a parsován z PDF/DOCX formátu.

    DŮLEŽITÉ: Tato informace je pouze informativní. Vždy se řiďte pokyny lékaře.

    Args:
        sukl_code: SÚKL kód přípravku (např. "0254045")

    Returns:
        PILContent s obsahem letáku nebo None pokud dokument není dostupný

    Examples:
        - get_pil_content("0254045")
    """
    if ctx:
        await ctx.info(f"Načítám příbalový leták pro: {sukl_code}")
        await ctx.report_progress(progress=0, total=100)

    client = await get_sukl_client()
    parser = get_document_parser()
    sukl_code = sukl_code.strip().zfill(7)

    if ctx:
        await ctx.report_progress(progress=20, total=100)

    # Získej detail pro název
    detail = await client.get_medicine_detail(sukl_code)
    if not detail:
        return None

    medicine_name = detail.get("NAZEV", detail.get("nazev", ""))

    # Parsuj dokument
    try:
        doc_data = await parser.get_document_content(sukl_code=sukl_code, doc_type="pil")

        return PILContent(
            sukl_code=sukl_code,
            medicine_name=medicine_name,
            document_url=doc_data["url"],
            language="cs",
            full_text=doc_data["content"],
            document_format=doc_data["format"],
        )

    except (SUKLDocumentError, SUKLParseError) as e:
        logger.warning(f"Chyba při získávání PIL pro {sukl_code}: {e}")
        # Fallback: vrátit pouze URL
        return PILContent(
            sukl_code=sukl_code,
            medicine_name=medicine_name,
            document_url=f"https://prehledy.sukl.cz/pil/{sukl_code}.pdf",
            language="cs",
            full_text=f"Dokument není dostupný k automatickému parsování. "
            f"Pro zobrazení navštivte: https://prehledy.sukl.cz/pil/{sukl_code}.pdf",
            document_format=None,
        )


@mcp.tool(
    tags={"documents", "spc"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_spc_content(sukl_code: str, ctx: Context | None = None) -> PILContent | None:
    """
    Získá obsah Souhrnu údajů o přípravku (SPC) pro odborníky.

    SPC obsahuje detailní farmakologické informace, indikace, kontraindikace,
    interakce a další odborné údaje pro zdravotnické pracovníky.

    Args:
        sukl_code: SÚKL kód přípravku (např. "0254045")

    Returns:
        PILContent s obsahem SPC nebo None pokud dokument není dostupný

    Examples:
        - get_spc_content("0254045")
    """
    if ctx:
        await ctx.info(f"Načítám SPC pro: {sukl_code}")
        await ctx.report_progress(progress=0, total=100)

    client = await get_sukl_client()
    parser = get_document_parser()
    sukl_code = sukl_code.strip().zfill(7)

    if ctx:
        await ctx.report_progress(progress=20, total=100)

    # Získej detail pro název
    detail = await client.get_medicine_detail(sukl_code)
    if not detail:
        return None

    medicine_name = detail.get("NAZEV", detail.get("nazev", ""))

    # Parsuj dokument
    try:
        doc_data = await parser.get_document_content(sukl_code=sukl_code, doc_type="spc")

        return PILContent(
            sukl_code=sukl_code,
            medicine_name=medicine_name,
            document_url=doc_data["url"],
            language="cs",
            full_text=doc_data["content"],
            document_format=doc_data["format"],
        )

    except (SUKLDocumentError, SUKLParseError) as e:
        logger.warning(f"Chyba při získávání SPC pro {sukl_code}: {e}")
        # Fallback: vrátit pouze URL
        return PILContent(
            sukl_code=sukl_code,
            medicine_name=medicine_name,
            document_url=f"https://prehledy.sukl.cz/spc/{sukl_code}.pdf",
            language="cs",
            full_text=f"Dokument není dostupný k automatickému parsování. "
            f"Pro zobrazení navštivte: https://prehledy.sukl.cz/spc/{sukl_code}.pdf",
            document_format=None,
        )


@mcp.tool(
    tags={"availability", "alternatives"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def check_availability(
    sukl_code: str,
    include_alternatives: bool = True,
    limit: int = 5,
    ctx: Context | None = None,
) -> AvailabilityInfo | None:
    """
    Zkontroluje aktuální dostupnost léčivého přípravku na českém trhu.

    EPIC 4: Pokud je přípravek nedostupný, automaticky najde a doporučí alternativy
    se stejnou účinnou látkou nebo ve stejné ATC skupině.

    Args:
        sukl_code: SÚKL kód přípravku
        include_alternatives: Zda zahrnout alternativy (default: True)
        limit: Max počet alternativ (default: 5, max: 10)

    Returns:
        AvailabilityInfo s informacemi o dostupnosti a alternativách
    """
    if ctx:
        await ctx.info(f"Kontroluji dostupnost: {sukl_code}")

    client = await get_sukl_client()
    sukl_code = sukl_code.strip().zfill(7)

    # Získej detail přípravku
    detail = await client.get_medicine_detail(sukl_code)
    if not detail:
        return None

    # Zkontroluj dostupnost pomocí normalizace
    availability = client._normalize_availability(detail.get("DODAVKY"))

    is_available = availability == AvailabilityStatus.AVAILABLE

    # Hledání alternativ (pouze pokud není dostupný)
    alternatives = []
    recommendation = None

    if include_alternatives and not is_available:
        # Použij find_generic_alternatives pro nalezení alternativ
        alt_results = await client.find_generic_alternatives(sukl_code, limit=limit)

        # Konverze na AlternativeMedicine modely
        for alt in alt_results:
            alternatives.append(
                AlternativeMedicine(
                    sukl_code=str(alt.get("KOD_SUKL", "")),
                    name=alt.get("NAZEV", ""),
                    strength=alt.get("SILA"),
                    form=alt.get("FORMA"),
                    is_available=True,
                    has_reimbursement=alt.get("has_reimbursement"),
                    relevance_score=alt.get("relevance_score", 0.0),
                    match_reason=alt.get("match_reason", "Similar medicine"),
                    max_price=alt.get("max_price"),
                    patient_copay=alt.get("patient_copay"),
                )
            )

        # Generuj doporučení
        if alternatives:
            top_alt = alternatives[0]
            recommendation = (
                f"Tento přípravek není dostupný. "
                f"Doporučujeme alternativu: {top_alt.name} "
                f"(relevance: {top_alt.relevance_score:.0f}/100, "
                f"důvod: {top_alt.match_reason})"
            )
        else:
            recommendation = "Tento přípravek není dostupný a nebyly nalezeny žádné alternativy."

    return AvailabilityInfo(
        sukl_code=sukl_code,
        name=detail.get("NAZEV", ""),
        is_available=is_available,
        status=availability,
        alternatives_available=len(alternatives) > 0,
        alternatives=alternatives,
        recommendation=recommendation,
        checked_at=datetime.now(),
    )


@mcp.tool(
    tags={"pricing", "reimbursement"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_reimbursement(sukl_code: str, ctx: Context | None = None) -> ReimbursementInfo | None:
    """
    Získá informace o úhradě léčivého přípravku zdravotní pojišťovnou.

    Vrací maximální cenu, výši úhrady pojišťovny a doplatek pacienta
    podle aktuálních cenových předpisů SÚKL (dlp_cau.csv).

    POZNÁMKA: Skutečný doplatek se může lišit podle konkrétní pojišťovny
    a bonusových programů lékáren.

    Args:
        sukl_code: SÚKL kód přípravku (7 číslic, např. "0012345")

    Returns:
        ReimbursementInfo s cenovými a úhradovými informacemi nebo None

    Examples:
        - get_reimbursement("0012345")
    """
    if ctx:
        await ctx.info(f"Načítám úhradové informace pro: {sukl_code}")

    client = await get_sukl_client()
    sukl_code = sukl_code.strip().zfill(7)

    # Získej základní informace o léčivu
    detail = await client.get_medicine_detail(sukl_code)
    if not detail:
        return None

    # Získej cenové a úhradové informace z dlp_cau
    price_info = await client.get_price_info(sukl_code)

    # Sestavení response
    if price_info:
        return ReimbursementInfo(
            sukl_code=sukl_code,
            medicine_name=detail.get("NAZEV", ""),
            is_reimbursed=price_info.get("is_reimbursed", False),
            reimbursement_group=price_info.get("indication_group"),
            max_producer_price=price_info.get("max_price"),
            max_retail_price=price_info.get("max_price"),  # Stejná hodnota jako max_producer_price
            reimbursement_amount=price_info.get("reimbursement_amount"),
            patient_copay=price_info.get("patient_copay"),
            has_indication_limit=bool(price_info.get("indication_group")),
            indication_limit_text=price_info.get("indication_group"),
            specialist_only=False,  # TODO: Pokud bude v CSV
        )
    else:
        # Fallback pokud nejsou cenová data
        return ReimbursementInfo(
            sukl_code=sukl_code,
            medicine_name=detail.get("NAZEV", ""),
            is_reimbursed=False,
            reimbursement_group=None,
            max_producer_price=None,
            max_retail_price=None,
            reimbursement_amount=None,
            patient_copay=None,
            has_indication_limit=False,
            indication_limit_text=None,
            specialist_only=False,
        )


@mcp.tool(
    tags={"pharmacies", "search"},
    annotations={"readOnlyHint": True, "openWorldHint": True, "idempotentHint": True},
)
async def find_pharmacies(
    city: str | None = None,
    postal_code: str | None = None,
    has_24h_service: bool = False,
    has_internet_sales: bool = False,
    limit: int = 20,
    ctx: Context | None = None,
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
    if ctx:
        location = city or postal_code or "celá ČR"
        await ctx.info(f"Hledám lékárny: {location}")

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


@mcp.tool(
    tags={"classification", "atc"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_atc_info(atc_code: str, ctx: Context | None = None) -> ATCInfo:
    """
    Získá informace o ATC (anatomicko-terapeuticko-chemické) skupině.

    ATC klasifikace dělí léčiva do skupin podle anatomické skupiny,
    terapeutické skupiny a chemické substance.

    Args:
        atc_code: ATC kód (1-7 znaků, např. 'N', 'N02', 'N02BE01')

    Returns:
        ATCInfo s informacemi o ATC skupině včetně podskupin

    Examples:
        - get_atc_info("N") - Léčiva nervového systému
        - get_atc_info("N02") - Analgetika
        - get_atc_info("N02BE01") - Paracetamol
    """
    if ctx:
        await ctx.info(f"Načítám ATC skupinu: {atc_code}")

    client = await get_sukl_client()
    atc_code = atc_code.upper().strip()

    groups = await client.get_atc_groups(atc_code if len(atc_code) < 7 else None)

    # Najdi konkrétní skupinu
    # DŮLEŽITÉ: ATC tabulka má sloupce 'ATC' a 'NAZEV' (ne 'kod')
    target = None
    children: list[ATCChild] = []

    for group in groups:
        code = group.get("ATC", "")  # Sloupec v dlp_atc.csv
        name = group.get("NAZEV", "")  # Sloupec v dlp_atc.csv
        if code == atc_code:
            target = group
        elif code.startswith(atc_code) and len(code) > len(atc_code):
            children.append(
                ATCChild(
                    code=code,
                    name=name,
                )
            )

    return ATCInfo(
        code=atc_code,
        name=target.get("NAZEV", "Neznámá skupina") if target else "Neznámá skupina",
        level=min(len(atc_code), 5),
        children=children[:20],
        total_children=len(children),
    )


# === Nové nástroje využívající REST API ===


@mcp.tool(
    tags={"availability", "hsz", "unavailable"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_unavailable_medicines(
    unavailability_type: str | None = None,
    limit: int = 50,
    ctx: Context | None = None,
) -> UnavailabilityReport:
    """
    Získá seznam nedostupných léčivých přípravků z databáze HSZ (Hlášení skladových zásob).

    Používá real-time REST API pro aktuální data o nedostupnosti léčiv.

    Args:
        unavailability_type: Typ nedostupnosti - 'JR' (jednorázový požadavek) nebo 'OOP' (omezená dostupnost)
        limit: Maximální počet vrácených záznamů (výchozí 50)

    Returns:
        UnavailabilityReport se seznamem nedostupných LP a statistikami

    Examples:
        - get_unavailable_medicines() - Všechny nedostupné LP
        - get_unavailable_medicines(unavailability_type="OOP") - Pouze s omezenou dostupností
    """
    if ctx:
        await ctx.info("Načítám seznam nedostupných léčiv z HSZ API...")

    api_client = await SUKLAPIClient.get_instance()

    # Mapování typu
    type_filter = None
    if unavailability_type:
        if unavailability_type.upper() == "JR":
            type_filter = 1
        elif unavailability_type.upper() == "OOP":
            type_filter = 2

    unavailable = await api_client.get_unavailable_medicines(type_filter)

    # Konverze na modely
    medicines = []
    jr_count = 0
    oop_count = 0

    for med in unavailable[:limit]:
        med_type = UnavailabilityType.ONE_TIME if med.typ == 1 else UnavailabilityType.LIMITED
        if med.typ == 1:
            jr_count += 1
        else:
            oop_count += 1

        # Mapování periodicity
        periodicity_map = {1: "jednorázově", 2: "denně", 3: "týdně", 4: "měsíčně"}
        frequency = periodicity_map.get(med.periodicita) if med.periodicita else None

        # Mapování skupin hlásitelů
        reporter_map = {"lek": "lékárny", "dis": "distributoři", "mah": "držitelé registrace"}
        reporters = [reporter_map.get(r, r) for r in (med.skupina_hlasitelu or [])]

        medicines.append(
            UnavailableMedicineInfo(
                sukl_code=med.kod_sukl,
                name=med.nazev,
                supplement=med.doplnek,
                unavailability_type=med_type,
                valid_from=datetime.strptime(med.plat_od, "%Y-%m-%d") if med.plat_od else None,
                valid_to=datetime.strptime(med.plat_do, "%Y-%m-%d") if med.plat_do else None,
                reporting_frequency=frequency,
                required_reporters=reporters,
            )
        )

    return UnavailabilityReport(
        total_count=len(unavailable),
        one_time_requests=jr_count,
        limited_availability=oop_count,
        medicines=medicines,
    )


@mcp.tool(
    tags={"market", "status", "availability"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_market_status(
    sukl_code: str,
    ctx: Context | None = None,
) -> MarketReportInfo | None:
    """
    Získá aktuální stav uvádění léčivého přípravku na trh z market reportu.

    Informace o tom, zda je přípravek aktivně uváděn na trh, přerušen nebo ukončen.

    Args:
        sukl_code: 7místný kód SÚKL

    Returns:
        MarketReportInfo s informacemi o stavu uvádění na trh, nebo None pokud není nalezen

    Examples:
        - get_market_status("0254045") - Stav PARALEN 500MG na trhu
    """
    if ctx:
        await ctx.info(f"Kontroluji stav uvádění na trh pro: {sukl_code}")

    api_client = await SUKLAPIClient.get_instance()
    report = await api_client.get_market_report_for_medicine(sukl_code)

    if not report:
        return None

    return MarketReportInfo(
        sukl_code=report.kod_sukl,
        notification_type=MarketNotificationType(report.typ_oznameni),
        valid_from=datetime.strptime(report.plat_od, "%Y-%m-%d") if report.plat_od else None,
        reported_at=(
            datetime.strptime(report.datum_hlaseni, "%Y-%m-%d") if report.datum_hlaseni else None
        ),
        replacement_medicines=report.nahrazujici_lp or [],
        suspension_reason=report.duvod_preruseni,
        expected_resume_date=(
            datetime.strptime(report.termin_obnovy, "%Y-%m-%d") if report.termin_obnovy else None
        ),
        note=report.poznamka,
    )


@mcp.tool(
    tags={"pharmacy", "search", "realtime"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def search_pharmacies_live(
    city: str,
    limit: int = 20,
    ctx: Context | None = None,
) -> list[PharmacyInfo]:
    """
    Vyhledá lékárny v daném městě pomocí real-time REST API.

    Na rozdíl od find_pharmacies používá živá data z API (ne CSV cache).
    Obsahuje detailnější informace včetně otevírací doby a GPS souřadnic.

    Args:
        city: Název města (např. 'Praha', 'Brno')
        limit: Maximální počet výsledků (výchozí 20, max 100)

    Returns:
        Seznam PharmacyInfo s detaily lékáren

    Examples:
        - search_pharmacies_live("Praha") - Lékárny v Praze
        - search_pharmacies_live("Brno", limit=10) - 10 lékáren v Brně
    """
    if ctx:
        await ctx.info(f"Vyhledávám lékárny v městě: {city}")

    api_client = await SUKLAPIClient.get_instance()
    pharmacies = await api_client.search_pharmacies_by_city(city, min(limit, 100))

    results = []
    for p in pharmacies:
        info = pharmacy_api_to_info(p)
        results.append(PharmacyInfo(**info))

    return results


@mcp.tool(
    tags={"price", "reimbursement", "realtime"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_live_price(
    sukl_code: str,
    ctx: Context | None = None,
) -> ReimbursementInfo | None:
    """
    Získá aktuální cenové a úhradové informace z REST API.

    Používá real-time API pro nejaktuálnější data o cenách a úhradách.
    Vhodné pro léčiva se stanovenou úhradou (CAU/SCAU).

    Args:
        sukl_code: 7místný kód SÚKL

    Returns:
        ReimbursementInfo s aktuálními cenovými údaji, nebo None pokud LP nemá úhradu

    Examples:
        - get_live_price("0000113") - Cena DILURAN (má úhradu)
    """
    if ctx:
        await ctx.info(f"Načítám aktuální ceny pro: {sukl_code}")

    api_client = await SUKLAPIClient.get_instance()
    price_info = await api_client.get_price_reimbursement(sukl_code)

    if not price_info:
        return None

    # Zpracování úhrad
    is_reimbursed = bool(price_info.uhrady)
    reimbursement_amount = None
    patient_copay = None

    if price_info.uhrady and len(price_info.uhrady) > 0:
        first_uhrada = price_info.uhrady[0]
        reimbursement_amount = first_uhrada.get("uhradaZaBaleni")
        patient_copay = first_uhrada.get("doplatek")

    return ReimbursementInfo(
        sukl_code=sukl_code,
        medicine_name=price_info.nazev or "",
        is_reimbursed=is_reimbursed,
        reimbursement_group=None,  # API neposkytuje
        max_producer_price=price_info.cena_puvodce,
        max_retail_price=price_info.cena_lekarna,
        reimbursement_amount=reimbursement_amount,
        patient_copay=patient_copay,
        has_indication_limit=False,  # Vyžaduje detailní analýzu
        indication_limit_text=None,
        specialist_only=False,
    )


@mcp.tool(
    tags={"vaccine", "batch", "safety"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_vaccine_batches(
    sukl_code: str | None = None,
    limit: int = 50,
    ctx: Context | None = None,
) -> VaccineBatchReport:
    """
    Získá seznam propuštěných šarží vakcín.

    Důležité pro sledování bezpečnosti vakcín a ověření šarže.

    Args:
        sukl_code: Volitelný filtr - SÚKL kód vakcíny (7 číslic)
        limit: Maximální počet šarží (výchozí 50)

    Returns:
        VaccineBatchReport se seznamem šarží a datem poslední aktualizace

    Examples:
        - get_vaccine_batches() - Všechny propuštěné šarže vakcín
        - get_vaccine_batches("0250303") - Šarže konkrétní vakcíny
    """
    if ctx:
        await ctx.info("Načítám seznam propuštěných šarží vakcín...")

    api_client = await SUKLAPIClient.get_instance()
    batches, last_change = await api_client.get_vaccine_batches(sukl_code)

    # Konverze na modely
    batch_infos = []
    for b in batches[:limit]:
        released = None
        expiration = None

        # Parse date formats (DD.MM.YYYY)
        if b.propusteno_dne:
            try:
                released = datetime.strptime(b.propusteno_dne, "%d.%m.%Y")
            except ValueError:
                pass

        if b.expirace:
            try:
                expiration = datetime.strptime(b.expirace, "%d.%m.%Y")
            except ValueError:
                pass

        batch_infos.append(
            VaccineBatchInfo(
                sukl_code=b.kod_sukl,
                vaccine_name=b.nazev,
                batch_number=b.sarze,
                released_date=released,
                expiration_date=expiration,
            )
        )

    # Parse last update
    last_update = None
    if last_change:
        try:
            last_update = datetime.strptime(last_change, "%d.%m.%Y")
        except ValueError:
            pass

    return VaccineBatchReport(
        total_batches=len(batches),
        last_update=last_update,
        batches=batch_infos,
    )


@mcp.tool(
    tags={"distributor", "supply"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_distributors(
    limit: int = 50,
    ctx: Context | None = None,
) -> list[DistributorInfo]:
    """
    Získá seznam distributorů léčiv v ČR.

    Distributoři jsou subjekty oprávněné k velkoobchodní distribuci léčiv.

    Args:
        limit: Maximální počet distributorů (výchozí 50)

    Returns:
        Seznam DistributorInfo s informacemi o distributorech

    Examples:
        - get_distributors() - Seznam distributorů léčiv
    """
    if ctx:
        await ctx.info("Načítám seznam distributorů léčiv...")

    api_client = await SUKLAPIClient.get_instance()
    distributors = await api_client.get_all_distributors()

    results = []
    for d in distributors[:limit]:
        # Sestavení adresy
        addr = d.adresa
        street = None
        city = None
        psc = None

        if addr:
            parts = []
            if addr.ulice:
                parts.append(addr.ulice)
            if addr.cislo_popisne:
                parts.append(addr.cislo_popisne)
            street = " ".join(parts) if parts else None
            psc = addr.psc

        # Sídlo
        sidlo = d.sidlo
        has_sukl = sidlo.povoleni_sukl if sidlo else False
        has_eu = sidlo.povoleni_eu if sidlo else False
        has_dispensing = sidlo.povoleni_vydeje if sidlo else False

        # Kontakty (null-safe)
        contacts = d.kontakty
        phones = contacts.get("tel", []) if contacts else []
        emails = contacts.get("email", []) if contacts else []
        webs = contacts.get("web", []) if contacts else []

        results.append(
            DistributorInfo(
                workplace_code=d.kod_pracoviste,
                name=d.nazev,
                ico=d.ico,
                type=d.typ,
                street=street,
                city=city,
                postal_code=psc,
                country="CZ",
                has_sukl_permit=has_sukl,
                has_eu_permit=has_eu,
                has_dispensing_permit=has_dispensing,
                phone=phones,
                email=emails,
                web=webs,
                is_active=True,
            )
        )

    return results


# === MCP Resources (Best Practice) ===
# Statická referenční data exponovaná přímo pro LLM


@mcp.resource(
    "sukl://health",
    tags={"system", "monitoring"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_health_resource() -> dict:
    """
    Aktuální stav serveru a statistiky databáze.

    Poskytuje informace o:
    - Stavu serveru (online/offline)
    - Počtu načtených záznamů
    - Čase posledního načtení dat
    """
    client = await get_sukl_client()
    health = await client.health_check()
    return health


@mcp.resource(
    "sukl://atc-groups/top-level",
    tags={"classification", "atc", "reference"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_top_level_atc_groups() -> dict:
    """
    Seznam hlavních ATC skupin (1. úroveň klasifikace).

    ATC = Anatomicko-terapeuticko-chemická klasifikace léčiv.
    Vrací 14 hlavních skupin (A-V) s jejich názvy.
    """
    client = await get_sukl_client()
    groups = await client.get_atc_groups(None)

    # Filtruj pouze top-level skupiny (1 znak)
    # DŮLEŽITÉ: ATC tabulka má sloupce 'ATC' a 'NAZEV'
    top_level = [
        {"code": g.get("ATC", ""), "name": g.get("NAZEV", "")}
        for g in groups
        if len(g.get("ATC", "")) == 1
    ]

    return {
        "description": "Hlavní ATC skupiny (1. úroveň)",
        "total": len(top_level),
        "groups": top_level,
    }


@mcp.resource(
    "sukl://statistics",
    tags={"system", "statistics"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_database_statistics() -> dict:
    """
    Statistiky databáze léčiv.

    Poskytuje souhrnné informace o počtech:
    - Celkový počet léčivých přípravků
    - Počet dostupných přípravků
    - Počet hrazených přípravků
    """
    client = await get_sukl_client()

    # Získej základní statistiky
    total_medicines = 0
    available_count = 0

    dlp = client._loader.get_table("dlp")
    if dlp is not None:
        total_medicines = len(dlp)
        if "DODAVKY" in dlp.columns:
            available_count = int((dlp["DODAVKY"] == "A").sum())

    return {
        "total_medicines": total_medicines,
        "available_medicines": available_count,
        "unavailable_medicines": total_medicines - available_count,
        "data_source": "SÚKL Open Data",
        "server_version": "3.1.0",
    }


# === MCP Resource Templates (Dynamic Resources) ===
# Dynamické zdroje s parametry v URI


@mcp.resource(
    "sukl://medicine/{sukl_code}",
    tags={"medicines", "detail"},
    annotations={"readOnlyHint": True},
)
async def get_medicine_resource(sukl_code: str) -> dict:
    """
    Detailní informace o léčivu jako resource (bez volání tool).

    Parametry URI:
        sukl_code: SÚKL kód přípravku (7 číslic)

    Vrací kompletní informace o léčivém přípravku včetně cen.
    """
    client = await get_sukl_client()
    sukl_code = sukl_code.strip().zfill(7)

    data = await client.get_medicine_detail(sukl_code)
    if not data:
        return {"error": f"Léčivo {sukl_code} nebylo nalezeno"}

    price_info = await client.get_price_info(sukl_code)

    return {
        "sukl_code": sukl_code,
        "name": data.get("NAZEV", ""),
        "supplement": data.get("DOPLNEK"),
        "strength": data.get("SILA"),
        "form": data.get("FORMA"),
        "atc_code": data.get("ATC_WHO"),
        "registration_holder": data.get("DRZ"),
        "is_available": data.get("DODAVKY") != "0",
        "dispensation_mode": data.get("VYDEJ"),
        "price_info": price_info if price_info else None,
    }


@mcp.resource(
    "sukl://atc/{atc_code}",
    tags={"classification", "atc"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_atc_resource(atc_code: str) -> ATCInfo:
    """
    ATC skupina jako resource (bez volání tool).

    Parametry URI:
        atc_code: ATC kód (1-7 znaků, např. 'N', 'N02', 'N02BE01')

    Vrací informace o ATC skupině včetně podskupin.
    """
    client = await get_sukl_client()
    atc_code = atc_code.upper().strip()

    groups = await client.get_atc_groups(atc_code if len(atc_code) < 7 else None)

    # DŮLEŽITÉ: ATC tabulka má sloupce 'ATC' a 'NAZEV' (ne 'kod')
    target = None
    children: list[ATCChild] = []

    for group in groups:
        code = group.get("ATC", "")  # Sloupec v dlp_atc.csv
        name = group.get("NAZEV", "")  # Sloupec v dlp_atc.csv
        if code == atc_code:
            target = group
        elif code.startswith(atc_code) and len(code) > len(atc_code):
            children.append(
                ATCChild(
                    code=code,
                    name=name,
                )
            )

    return ATCInfo(
        code=atc_code,
        name=target.get("NAZEV", "Neznámá skupina") if target else "Neznámá skupina",
        level=min(len(atc_code), 5),
        children=children[:20],
        total_children=len(children),
    )


# === Entry point ===


def main() -> None:
    """Spusť MCP server s automatickou detekcí transportu."""
    import os

    # Detekce transportu z ENV
    transport_str = os.getenv("MCP_TRANSPORT", "stdio").lower()

    if transport_str in {"http", "sse", "streamable-http"}:
        # HTTP transport pro Smithery/Docker deployment
        transport: Literal["http", "sse", "streamable-http"] = transport_str  # type: ignore[assignment]
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))

        logger.info(f"Starting SÚKL MCP Server on {transport}://{host}:{port}")
        mcp.run(transport=transport, host=host, port=port)
    else:
        # STDIO transport pro FastMCP Cloud a lokální použití
        logger.info("Starting SÚKL MCP Server on stdio")
        mcp.run()  # Výchozí stdio transport


if __name__ == "__main__":
    main()
