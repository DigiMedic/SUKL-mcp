"""
SÚKL MCP Server - FastMCP server pro přístup k databázi léčiv.

Poskytuje AI agentům přístup k české databázi léčivých přípravků.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from rapidfuzz import fuzz
from fastmcp import Context, FastMCP
from fastmcp.dependencies import Progress, CurrentContext
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from fastmcp.server.middleware.timing import TimingMiddleware

# Absolutní importy pro FastMCP Cloud compatibility
from sukl_mcp.api import SUKLAPIClient, close_api_client, get_api_client
from sukl_mcp.client_csv import SUKLClient, close_sukl_client, get_sukl_client
from sukl_mcp.document_parser import close_document_parser, get_document_parser
from sukl_mcp.exceptions import SUKLAPIError, SUKLDocumentError, SUKLParseError
from sukl_mcp.models import (
    AvailabilityInfo,
    MedicineDetail,
    MedicineSearchResult,
    PharmacyInfo,
    PILContent,
    ReimbursementInfo,
    SearchResponse,
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# === Application Context (Best Practice) ===


@dataclass
class AppContext:
    """Typovaný aplikační kontext pro lifespan."""

    client: "SUKLClient"  # CSV client (legacy, fallback)
    api_client: "SUKLAPIClient"  # REST API client (v4.0+, preferred)
    initialized_at: datetime


# === Lifecycle management ===


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncGenerator[AppContext, None]:
    """Inicializace a cleanup serveru s typovaným kontextem."""
    logger.info("Starting SÚKL MCP Server v4.0 (REST API + CSV fallback)...")

    # Inicializace REST API klienta (primary)
    api_client = await get_api_client()
    api_health = await api_client.health_check()
    logger.info(f"REST API health: {api_health['status']}, latency: {api_health.get('latency_ms', 'N/A')}ms")

    # Inicializace CSV klienta (fallback)
    csv_client = await get_sukl_client()
    await csv_client.initialize()  # Cold Start fix
    csv_health = await csv_client.health_check()
    logger.info(f"CSV client health: {csv_health}")

    # Vrať typovaný kontext
    yield AppContext(
        client=csv_client,
        api_client=api_client,
        initialized_at=datetime.now(),
    )

    logger.info("Shutting down SÚKL MCP Server...")
    await close_api_client()
    await close_sukl_client()
    close_document_parser()


# === FastMCP instance ===

mcp = FastMCP(
    name="SÚKL MCP Server",
    version="4.0.0",
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


@mcp.prompt
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


@mcp.prompt
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


@mcp.prompt
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


# === Helper Functions ===


def _calculate_match_quality(query: str, medicine_name: str) -> tuple[float, str]:
    """
    Vypočítá match score a typ na základě similarity query a názvu léku.

    Args:
        query: Hledaný výraz (case-insensitive)
        medicine_name: Název léku z API

    Returns:
        tuple[float, str]: (match_score, match_type)
            - match_score: 0-100 (vyšší = lepší shoda)
            - match_type: "exact" | "substring" | "fuzzy"
    """
    query_lower = query.lower().strip()
    name_lower = medicine_name.lower().strip()

    # 1. Exact match - absolutní shoda
    if query_lower == name_lower:
        return 100.0, "exact"

    # 2. Substring match - query je podřetězec názvu
    if query_lower in name_lower:
        # Score based on length ratio (delší match = vyšší score)
        ratio = len(query_lower) / len(name_lower)
        score = 80.0 + (ratio * 15.0)  # 80-95 range
        return score, "substring"

    # 3. Fuzzy match - podobnost pomocí rapidfuzz
    fuzzy_score = fuzz.ratio(query_lower, name_lower)

    if fuzzy_score >= 80:
        return fuzzy_score, "fuzzy"

    # 4. Partial ratio - pro částečné shody
    partial_score = fuzz.partial_ratio(query_lower, name_lower)

    if partial_score >= 80:
        return partial_score * 0.9, "fuzzy"  # Mírně nižší score pro partial

    # 5. Token sort ratio - ignoruje pořadí slov
    token_score = fuzz.token_sort_ratio(query_lower, name_lower)

    # Minimální score je token_score * 0.8
    return max(token_score * 0.8, 20.0), "fuzzy"


# === MCP Tools ===


async def _try_rest_search(
    query: str, limit: int, typ_seznamu: str = "dlpo"
) -> tuple[list[dict], str] | None:
    """
    Pokusí se vyhledat přes REST API.

    Hybrid helper: Try REST API first, return None on failure for CSV fallback.

    Args:
        query: Hledaný text
        limit: Maximální počet výsledků
        typ_seznamu: Typ seznamu (default: "dlpo" - dostupné léčivé přípravky)

    Returns:
        tuple[list[dict], str]: (results, "rest_api") nebo None při chybě
    """
    try:
        api_client = await get_api_client()

        # Search pro získání kódů
        search_result = await api_client.search_medicines(
            query=query, typ_seznamu=typ_seznamu, limit=limit
        )

        if not search_result.codes:
            logger.info(f"REST API: žádné výsledky pro '{query}'")
            return [], "rest_api"

        # Batch fetch details
        medicines = await api_client.get_medicines_batch(
            search_result.codes[:limit], max_concurrent=5
        )

        # Convert APILecivyPripravek -> dict pro kompatibilitu
        results = []
        for med in medicines:
            # Calculate actual match quality based on query vs medicine name
            match_score, match_type = _calculate_match_quality(query, med.nazev)

            results.append(
                {
                    "kod_sukl": med.kodSUKL,
                    "nazev": med.nazev,
                    "doplnek": med.doplnek,
                    "sila": med.sila,
                    "forma": med.lekovaFormaKod,
                    "baleni": med.baleni,
                    "atc": med.ATCkod,
                    "stav_registrace": med.stavRegistraceKod,
                    "vydej": med.zpusobVydejeKod,
                    "dostupnost": "ano" if med.jeDodavka else "ne",
                    # Match metadata - calculated based on actual similarity
                    "match_score": match_score,
                    "match_type": match_type,
                }
            )

        # Enrich with price data from CSV (REST API doesn't have price fields)
        csv_client = await get_sukl_client()
        enriched_results = await csv_client._enrich_with_price_data(results)

        logger.info(f"✅ REST API: {len(enriched_results)}/{len(search_result.codes)} results (enriched)")
        return enriched_results, "rest_api"

    except (SUKLAPIError, Exception) as e:
        logger.warning(f"⚠️  REST API search failed: {e}")
        return None


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
    Vyhledá léčivé přípravky v databázi SÚKL (v4.0: REST API + CSV fallback).

    Vyhledává podle názvu přípravku, účinné látky nebo ATC kódu s fuzzy matchingem.

    v4.0 Hybrid Mode:
    1. PRIMARY: REST API (prehledy.sukl.cz) - real-time data
    2. FALLBACK: CSV client - local cache

    Multi-level pipeline (CSV fallback):
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
    start_time = datetime.now()

    # Context-aware logging
    if ctx:
        await ctx.info(f"Searching for: {query}")
        if only_available:
            await ctx.debug("Filter: only available medicines")
        if only_reimbursed:
            await ctx.debug("Filter: only reimbursed medicines")

    # TRY: REST API (primary)
    rest_result = await _try_rest_search(query, limit)

    if rest_result is not None:
        # REST API success
        raw_results, match_type = rest_result
        if ctx:
            await ctx.info(f"Found {len(raw_results)} results via REST API")
    else:
        # FALLBACK: CSV client
        logger.info(f"🔄 Falling back to CSV for query: '{query}'")
        if ctx:
            await ctx.warning("REST API unavailable, using CSV fallback")
            # Use context for client access
            app_ctx = ctx.request_context.lifespan_context
            client = app_ctx.client
        else:
            # FALLBACK: Use global getter (backward compatible)
            client = await get_sukl_client()

        raw_results, match_type = await client.search_medicines(
            query=query,
            limit=limit,
            only_available=only_available,
            only_reimbursed=only_reimbursed,
            use_fuzzy=use_fuzzy,
        )
        match_type = f"csv_{match_type}"
        if ctx:
            await ctx.info(f"Found {len(raw_results)} results via CSV")

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


async def _try_rest_get_detail(sukl_code: str) -> dict | None:
    """
    Pokusí se získat detail přes REST API.

    Hybrid helper: Try REST API first, return None on failure for CSV fallback.

    Args:
        sukl_code: SÚKL kód (7 číslic)

    Returns:
        dict s daty léčiva nebo None při chybě
    """
    try:
        api_client = await get_api_client()

        # Get medicine detail from REST API
        medicine = await api_client.get_medicine(sukl_code)

        if not medicine:
            logger.info(f"REST API: medicine {sukl_code} not found")
            return None

        # Convert APILecivyPripravek → dict pro kompatibilitu
        data = {
            "NAZEV": medicine.nazev,
            "DOPLNEK": medicine.doplnek,
            "SILA": medicine.sila,
            "FORMA": medicine.lekovaFormaKod,
            "CESTA": medicine.cestaKod,
            "BALENI": medicine.baleni,
            "OBAL": medicine.obalKod,
            "RC": medicine.registracniCislo,
            "REG": medicine.stavRegistraceKod,
            "DRZ": medicine.drzitelKod,
            "ATC_WHO": medicine.ATCkod,
            "VYDEJ": medicine.zpusobVydejeKod,
            "DODAVKY": "1" if medicine.jeDodavka else "0",
            "ZAV": medicine.zavislostKod,
            "DOPING": medicine.dopingKod,
        }

        logger.info(f"✅ REST API: medicine detail for {sukl_code}")
        return data

    except (SUKLAPIError, Exception) as e:
        logger.warning(f"⚠️  REST API get_detail failed: {e}")
        return None


@mcp.tool(
    tags={"medicines", "details"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def get_medicine_details(
    sukl_code: str,
    ctx: Context | None = None,
) -> MedicineDetail | None:
    """
    Získá detailní informace o léčivém přípravku podle SÚKL kódu.

    Vrací kompletní informace včetně složení, registrace, cen, úhrad a dokumentů.

    v4.0: REST API + CSV fallback
    - PRIMARY: REST API (real-time data)
    - FALLBACK: CSV (local cache)
    - ALWAYS: Price data from CSV (dlp_cau.csv - REST API nemá ceny)

    Args:
        sukl_code: SÚKL kód léčivého přípravku (7 číslic, např. "0012345")

    Returns:
        MedicineDetail nebo None pokud přípravek neexistuje

    Examples:
        - get_medicine_details("0012345")
    """
    # Normalizace kódu
    sukl_code = sukl_code.strip().zfill(7)

    # Context-aware logging
    if ctx:
        await ctx.info(f"Getting details for medicine: {sukl_code}")

    # TRY: REST API pro základní data
    data = await _try_rest_get_detail(sukl_code)

    if data is None:
        # FALLBACK: CSV
        logger.info(f"🔄 Falling back to CSV for medicine: {sukl_code}")
        if ctx:
            await ctx.warning("REST API unavailable, using CSV fallback")
            # Use context for client access
            app_ctx = ctx.request_context.lifespan_context
            csv_client = app_ctx.client
        else:
            # FALLBACK: Use global getter (backward compatible)
            csv_client = await get_sukl_client()

        data = await csv_client.get_medicine_detail(sukl_code)

        if not data:
            if ctx:
                await ctx.warning(f"Medicine {sukl_code} not found")
            return None
    else:
        if ctx:
            await ctx.info("Retrieved medicine data via REST API")

    # Helper pro získání hodnoty z dict (velká písmena)
    def get_val(key_upper: str, default: str | None = None) -> str | None:
        """Získej hodnotu, podporuje jak velká tak malá písmena."""
        return data.get(key_upper, data.get(key_upper.lower(), default))

    # ALWAYS: Získej cenové údaje z CSV (REST API je nemá)
    if ctx:
        await ctx.debug("Fetching price info from CSV")
        app_ctx = ctx.request_context.lifespan_context
        csv_client = app_ctx.client
    else:
        csv_client = await get_sukl_client()

    price_info = await csv_client.get_price_info(sukl_code)

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
        # Note: None = data unavailable, False = not reimbursed, True = reimbursed
        has_reimbursement=price_info.get("is_reimbursed") if price_info else None,
        max_price=price_info.get("max_price") if price_info else None,
        reimbursement_amount=price_info.get("reimbursement_amount") if price_info else None,
        patient_copay=price_info.get("patient_copay") if price_info else None,
        pil_available=False,  # Vyžaduje volání parseru - kontrolováno při get_pil_content()
        spc_available=False,
        is_narcotic=get_val("ZAV") is not None and str(get_val("ZAV")) != "nan",
        is_psychotropic=False,
        is_doping=get_val("DOPING") is not None and str(get_val("DOPING")) != "nan",
        last_updated=datetime.now(),
    )


@mcp.tool(
    tags={"documents", "patient-info"},
    annotations={"readOnlyHint": True},
)
async def get_pil_content(
    sukl_code: str,
    ctx: Context | None = None,
) -> PILContent | None:
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
    sukl_code = sukl_code.strip().zfill(7)

    # Context-aware logging
    if ctx:
        await ctx.info(f"Fetching PIL (patient info) for medicine: {sukl_code}")

    # Get client and parser
    if ctx:
        app_ctx = ctx.request_context.lifespan_context
        client = app_ctx.client
    else:
        client = await get_sukl_client()

    parser = get_document_parser()

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
    tags={"documents", "professional-info"},
    annotations={"readOnlyHint": True},
)
async def get_spc_content(
    sukl_code: str,
    ctx: Context | None = None,
) -> PILContent | None:
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
    sukl_code = sukl_code.strip().zfill(7)

    # Context-aware logging
    if ctx:
        await ctx.info(f"Fetching SPC (professional info) for medicine: {sukl_code}")

    # Get client and parser
    if ctx:
        app_ctx = ctx.request_context.lifespan_context
        client = app_ctx.client
    else:
        client = await get_sukl_client()

    parser = get_document_parser()

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

    v4.0: REST API + CSV fallback
    - PRIMARY: REST API (availability check)
    - FALLBACK: CSV (local cache)
    - ALWAYS: CSV pro find_generic_alternatives() (REST API nemá substance search)

    Args:
        sukl_code: SÚKL kód přípravku
        include_alternatives: Zda zahrnout alternativy (default: True)
        limit: Max počet alternativ (default: 5, max: 10)

    Returns:
        AvailabilityInfo s informacemi o dostupnosti a alternativách
    """
    sukl_code = sukl_code.strip().zfill(7)

    # Context-aware logging
    if ctx:
        await ctx.info(f"Checking availability for medicine: {sukl_code}")

    # TRY: REST API pro dostupnost
    detail = await _try_rest_get_detail(sukl_code)

    if detail is None:
        # FALLBACK: CSV
        logger.info(f"🔄 Falling back to CSV for availability check: {sukl_code}")
        if ctx:
            await ctx.warning("REST API unavailable, using CSV fallback")
            app_ctx = ctx.request_context.lifespan_context
            csv_client = app_ctx.client
        else:
            csv_client = await get_sukl_client()

        detail = await csv_client.get_medicine_detail(sukl_code)

        if not detail:
            if ctx:
                await ctx.warning(f"Medicine {sukl_code} not found")
            return None
    else:
        # Get CSV client for subsequent operations
        if ctx:
            app_ctx = ctx.request_context.lifespan_context
            csv_client = app_ctx.client
        else:
            csv_client = await get_sukl_client()

    # Zkontroluj dostupnost
    availability = csv_client._normalize_availability(detail.get("DODAVKY"))

    if ctx:
        await ctx.info(f"Availability status: {availability}")

    # Import zde pro circular dependency
    from sukl_mcp.models import AlternativeMedicine, AvailabilityStatus

    is_available = availability == AvailabilityStatus.AVAILABLE

    # Hledání alternativ (pokud je požadováno)
    alternatives = []
    recommendation = None

    if include_alternatives:
        if ctx:
            await ctx.info("Searching for alternatives")

        # Použij find_generic_alternatives pro nalezení alternativ
        alt_results = await csv_client.find_generic_alternatives(sukl_code, limit=limit)

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

        if ctx:
            await ctx.info(f"Found {len(alternatives)} alternative(s)")

        # Generuj doporučení
        if alternatives:
            top_alt = alternatives[0]
            if not is_available:
                # Lék není dostupný - doporuč alternativu
                recommendation = (
                    f"Tento přípravek není dostupný. "
                    f"Doporučujeme alternativu: {top_alt.name} "
                    f"(relevance: {top_alt.relevance_score:.0f}/100, "
                    f"důvod: {top_alt.match_reason})"
                )
            else:
                # Lék je dostupný - zobraz alternativy pro porovnání
                recommendation = (
                    f"Dostupných {len(alternatives)} alternativ. "
                    f"Nejlepší: {top_alt.name} "
                    f"(relevance: {top_alt.relevance_score:.0f}/100)"
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
async def get_reimbursement(
    sukl_code: str,
    ctx: Context | None = None,
) -> ReimbursementInfo | None:
    """
    Získá informace o úhradě léčivého přípravku zdravotní pojišťovnou.

    Vrací maximální cenu, výši úhrady pojišťovny a doplatek pacienta
    podle aktuálních cenových předpisů SÚKL (dlp_cau.csv).

    POZNÁMKA: Skutečný doplatek se může lišit podle konkrétní pojišťovny
    a bonusových programů lékáren.

    v4.0: PURE CSV (REST API nemá cenová data)
    - REST API **DOES NOT** provide price/reimbursement data
    - dlp_cau.csv is the **ONLY source** for pricing information
    - Optional REST API usage for medicine name only (faster)

    CRITICAL LIMITATION:
    SÚKL REST API endpoint '/dlp/v1/lecive-pripravky/{kod}' does NOT include
    fields for max_price, reimbursement_amount, or patient_copay. These data
    are only available in CSV file 'dlp_cau.csv' (cenové a úhradové údaje).

    Future (v4.1+): Consider background CSV sync → cache for hybrid mode.

    Args:
        sukl_code: SÚKL kód přípravku (7 číslic, např. "0012345")

    Returns:
        ReimbursementInfo s cenovými a úhradovými informacemi nebo None

    Examples:
        - get_reimbursement("0012345")
    """
    sukl_code = sukl_code.strip().zfill(7)

    # Context-aware logging
    if ctx:
        await ctx.info(f"Fetching reimbursement info for medicine: {sukl_code}")

    # OPTIONAL: REST API pro název léčiva (rychlejší než CSV)
    medicine_name = ""
    try:
        if ctx:
            app_ctx = ctx.request_context.lifespan_context
            api_client = app_ctx.api_client
        else:
            api_client = await get_api_client()

        medicine = await api_client.get_medicine(sukl_code)
        if medicine:
            medicine_name = medicine.nazev
            logger.info(f"✅ REST API: medicine name for {sukl_code}")
            if ctx:
                await ctx.debug("Retrieved medicine name via REST API")
    except (SUKLAPIError, Exception) as e:
        logger.debug(f"REST API name fetch failed: {e}, using CSV")
        if ctx:
            await ctx.debug("REST API failed, will use CSV for medicine name")
        pass  # Fallback na CSV název

    # ALWAYS: Získej základní informace a cenové údaje z CSV
    if ctx:
        app_ctx = ctx.request_context.lifespan_context
        csv_client = app_ctx.client
    else:
        csv_client = await get_sukl_client()

    if not medicine_name:
        detail = await csv_client.get_medicine_detail(sukl_code)
        if not detail:
            return None
        medicine_name = detail.get("NAZEV", "")

    # ALWAYS: Cenové a úhradové informace z dlp_cau (REST API je nemá)
    price_info = await csv_client.get_price_info(sukl_code)

    # Sestavení response
    if price_info:
        return ReimbursementInfo(
            sukl_code=sukl_code,
            medicine_name=medicine_name,
            is_reimbursed=price_info.get("is_reimbursed", False),
            reimbursement_group=price_info.get("indication_group"),
            max_producer_price=price_info.get("max_price"),
            max_retail_price=price_info.get("max_price"),  # Stejná hodnota jako max_producer_price
            reimbursement_amount=price_info.get("reimbursement_amount"),
            patient_copay=price_info.get("patient_copay"),
            has_indication_limit=bool(price_info.get("indication_group")),
            indication_limit_text=price_info.get("indication_group"),
            specialist_only=False,  # Data není v dlp_cau.csv
        )
    else:
        # Fallback pokud nejsou cenová data
        return ReimbursementInfo(
            sukl_code=sukl_code,
            medicine_name=medicine_name,
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
    tags={"pharmacies", "location"},
    annotations={"readOnlyHint": True, "openWorldHint": True},
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
    # Context-aware logging
    if ctx:
        filters = []
        if city:
            filters.append(f"city={city}")
        if postal_code:
            filters.append(f"postal_code={postal_code}")
        if has_24h_service:
            filters.append("24h service")
        if has_internet_sales:
            filters.append("internet sales")
        filter_str = ", ".join(filters) if filters else "no filters"
        await ctx.info(f"Searching pharmacies: {filter_str}")

    # Get client
    if ctx:
        app_ctx = ctx.request_context.lifespan_context
        client = app_ctx.client
    else:
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
async def get_atc_info(
    atc_code: str,
    ctx: Context | None = None,
) -> dict:
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
    # Context-aware logging
    if ctx:
        await ctx.info(f"Fetching ATC classification info for: {atc_code}")

    # Get client
    if ctx:
        app_ctx = ctx.request_context.lifespan_context
        client = app_ctx.client
    else:
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
        "name": (
            target.get("nazev", target.get("NAZEV", "Neznámá skupina"))
            if target
            else "Neznámá skupina"
        ),
        "level": len(atc_code) if len(atc_code) <= 5 else 5,
        "children": children[:20],
        "total_children": len(children),
    }


# === Background Tasks (Week 3: FastMCP Best Practices) ===


@mcp.tool(
    task=True,  # NEW: Background task
    tags={"availability", "batch", "background"},
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
async def batch_check_availability(
    sukl_codes: list[str],
    progress: Progress = Progress(),
    ctx: Context = CurrentContext(),
) -> dict:
    """
    Zkontroluje dostupnost více léčiv najednou na pozadí.

    Asynchronní batch operace pro kontrolu dostupnosti více léčiv současně.
    Podporuje progress tracking a běží na pozadí s in-memory nebo Redis backend.

    Args:
        sukl_codes: Seznam SÚKL kódů k ověření (např. ["0123456", "0234567"])
        progress: Progress tracker (automaticky injektován)
        ctx: Context pro logging (automaticky injektován, optional)

    Returns:
        Souhrn výsledků s celkovými statistikami a detaily pro každý lék

    Examples:
        - batch_check_availability(["0123456", "0234567"])
        - batch_check_availability(["0123456", "0234567", "0345678", ...])  # až 100 léků

    Note:
        - Development: Používá in-memory backend (výchozí)
        - Production: Vyžaduje Redis/Valkey pro distributed mode
        - Rate limiting: 0.1s mezi jednotlivými kontrolami
    """
    if not sukl_codes:
        return {"error": "No SÚKL codes provided", "total": 0, "available": 0, "results": []}

    # Limit maximum batch size
    if len(sukl_codes) > 100:
        await ctx.warning(f"Batch size {len(sukl_codes)} exceeds limit 100, truncating")
        sukl_codes = sukl_codes[:100]

    await progress.set_total(len(sukl_codes))

    await ctx.info(f"Starting batch availability check for {len(sukl_codes)} medicines")

    results = []
    available_count = 0

    for i, code in enumerate(sukl_codes):
        try:
            await progress.set_message(f"Checking {code} ({i+1}/{len(sukl_codes)})")

            # Call existing check_availability tool
            result = await check_availability(code, include_alternatives=False)

            is_available = result.is_available if result else False
            if is_available:
                available_count += 1

            results.append({
                "sukl_code": code,
                "is_available": is_available,
                "name": result.name if result else None,
            })

            await progress.increment()

            # Rate limiting to prevent overload
            await asyncio.sleep(0.1)

        except Exception as e:
            logger.warning(f"Error checking availability for {code}: {e}")
            results.append({
                "sukl_code": code,
                "is_available": False,
                "error": str(e),
            })
            await progress.increment()

    await ctx.info(
        f"Batch check complete: {available_count}/{len(sukl_codes)} medicines available"
    )

    return {
        "total": len(sukl_codes),
        "available": available_count,
        "unavailable": len(sukl_codes) - available_count,
        "results": results,
    }


# === MCP Resources (Best Practice) ===
# Statická referenční data exponovaná přímo pro LLM


@mcp.resource("sukl://health")
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


@mcp.resource("sukl://atc-groups/top-level")
async def get_top_level_atc_groups() -> dict:
    """
    Seznam hlavních ATC skupin (1. úroveň klasifikace) s navigačními URI.

    ATC = Anatomicko-terapeuticko-chemická klasifikace léčiv.
    Vrací 14 hlavních skupin (A-V) s jejich názvy a odkazy pro procházení hierarchie.
    """
    client = await get_sukl_client()
    groups = await client.get_atc_groups(None)

    # Filtruj pouze top-level skupiny (1 znak) a přidej URI
    top_level = [
        {
            "code": g.get("kod", g.get("KOD", "")),
            "name": g.get("nazev", g.get("NAZEV", "")),
            "uri": f"sukl://atc/{g.get('kod', g.get('KOD', ''))}",  # Add navigation URI
        }
        for g in groups
        if len(g.get("kod", g.get("KOD", ""))) == 1
    ]

    return {
        "description": "Hlavní ATC skupiny (1. úroveň) s navigačními URI",
        "total": len(top_level),
        "groups": top_level,
    }


@mcp.resource("sukl://atc/level/{level}")
async def get_atc_by_level(level: int) -> dict:
    """
    Browse ATC codes by hierarchical level (1-5).

    Level 1: Anatomical (14 groups) - A,B,C,D,G,H,J,L,M,N,P,R,S,V
    Level 2: Therapeutic (~80 groups)
    Level 3: Pharmacological (~250 groups)
    Level 4: Chemical (~900 groups)
    Level 5: Substance (~5,700 codes)
    """
    if not 1 <= level <= 5:
        raise ValueError("Level must be 1-5")

    client = await get_sukl_client()
    df = client._loader.get_table("dlp_atc")

    # Filter by code length (level 1 = 1 char, level 2 = 3 chars, etc.)
    code_lengths = {1: 1, 2: 3, 3: 4, 4: 5, 5: 7}
    target_length = code_lengths[level]

    filtered = df[df["KOD"].str.len() == target_length]

    return {
        "level": level,
        "total": len(filtered),
        "codes": [
            {
                "code": row["KOD"],
                "name": row["NAZEV"],
                "name_en": row.get("NAZEV_EN"),
            }
            for _, row in filtered.head(100).iterrows()  # Limit 100 per level
        ],
    }


@mcp.resource("sukl://atc/{code}")
async def get_atc_code_resource(code: str) -> dict:
    """
    Get ATC code details with parent and children navigation.

    Examples:
    - sukl://atc/N → Nervous system (level 1)
    - sukl://atc/N02 → Analgesics (level 2)
    - sukl://atc/N02BE → Anilides (level 3)
    - sukl://atc/N02BE01 → Paracetamol (level 5)
    """
    client = await get_sukl_client()
    df = client._loader.get_table("dlp_atc")

    # Get current code
    current = df[df["KOD"] == code.upper()]
    if current.empty:
        return {"error": f"ATC code {code} not found", "code": code}

    row = current.iloc[0]
    code_len = len(code)

    # Determine level
    level_map = {1: 1, 3: 2, 4: 3, 5: 4, 7: 5}
    level = level_map.get(code_len, 0)

    # Get parent (1 level up)
    parent_code = None
    if code_len > 1:
        parent_lengths = {3: 1, 4: 3, 5: 4, 7: 5}
        parent_len = parent_lengths.get(code_len)
        if parent_len:
            parent_code = code[:parent_len]

    # Get children (1 level down)
    children = []
    if level < 5:  # Not at substance level
        child_df = df[df["KOD"].str.startswith(code) & (df["KOD"].str.len() > code_len)]
        # Group by next level length
        next_lengths = {1: 3, 3: 4, 4: 5, 5: 7}
        next_len = next_lengths.get(code_len)
        if next_len:
            child_df = child_df[child_df["KOD"].str.len() == next_len]
            children = [
                {"code": c["KOD"], "name": c["NAZEV"]} for _, c in child_df.head(20).iterrows()
            ]

    return {
        "code": row["KOD"],
        "name": row["NAZEV"],
        "name_en": row.get("NAZEV_EN"),
        "level": level,
        "parent": parent_code,
        "children": children,
        "total_children": len(children),
        "uri_parent": f"sukl://atc/{parent_code}" if parent_code else None,
        "uri_children": [f"sukl://atc/{c['code']}" for c in children[:5]],  # First 5
    }


@mcp.resource("sukl://atc/tree/{root_code}")
async def get_atc_subtree(root_code: str) -> dict:
    """
    Get complete subtree from ATC code (all descendants).

    Example: sukl://atc/tree/N02 → all analgesics
    Warning: Large subtrees may return 100+ codes
    """
    client = await get_sukl_client()
    df = client._loader.get_table("dlp_atc")

    # Get all codes starting with root_code
    subtree = df[df["KOD"].str.startswith(root_code.upper())]

    return {
        "root_code": root_code.upper(),
        "total_descendants": len(subtree),
        "codes": [
            {
                "code": row["KOD"],
                "name": row["NAZEV"],
                "level": {1: 1, 3: 2, 4: 3, 5: 4, 7: 5}.get(len(row["KOD"]), 0),
            }
            for _, row in subtree.head(100).iterrows()
        ],
    }


@mcp.resource("sukl://statistics")
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
        "server_version": "4.0.0",
    }


@mcp.resource("sukl://pharmacies/regions")
async def get_pharmacy_regions() -> list[str]:
    """
    Seznam všech českých krajů (14 krajů) pro regionální vyhledávání lékáren.

    Vrací seznam názvů krajů, které lze použít pro filtrování lékáren
    prostřednictvím resource sukl://pharmacies/region/{region_name}.
    """
    client = await get_sukl_client()
    df = client._loader.get_table("lekarny_seznam")

    if df is None or df.empty:
        return []

    # Get unique regions and sort them
    regions = df["KRAJ"].dropna().drop_duplicates().sort_values().tolist()
    return regions


@mcp.resource("sukl://pharmacies/region/{region_name}")
async def get_pharmacies_by_region(region_name: str) -> dict:
    """
    Seznam lékáren v konkrétním kraji.

    Args:
        region_name: Název kraje (např. "Praha", "Středočeský", "Jihomoravský")

    Returns:
        Slovník s celkovým počtem a seznamem lékáren (max 50).
    """
    client = await get_sukl_client()
    df = client._loader.get_table("lekarny_seznam")

    if df is None or df.empty:
        return {"region": region_name, "total": 0, "pharmacies": []}

    # Filter by region (case-insensitive partial match)
    filtered = df[df["KRAJ"].str.contains(region_name, case=False, na=False)]

    pharmacies = [
        {
            "name": row.get("NAZEV"),
            "city": row.get("MESTO"),
            "street": row.get("ULICE"),
            "postal_code": row.get("PSC"),
        }
        for _, row in filtered.head(50).iterrows()
    ]

    return {"region": region_name, "total": len(filtered), "pharmacies": pharmacies}


@mcp.resource("sukl://statistics/detailed")
async def get_detailed_statistics() -> dict:
    """
    Komplexní statistiky databáze SÚKL.

    Poskytuje podrobné informace o:
    - Léčivých přípravcích (celkem, dostupné, nedostupné)
    - Léčivých látkách
    - ATC hierarchii (počty na každé úrovni)
    - Lékárnách

    Rychlejší alternativa k opakovaným tool calls pro získání statistik.
    """
    client = await get_sukl_client()

    # Medicines stats
    dlp = client._loader.get_table("dlp")
    total_medicines = len(dlp) if dlp is not None else 0
    available_count = int((dlp["DODAVKY"] == "A").sum()) if dlp is not None and "DODAVKY" in dlp.columns else 0

    # Substances count
    substances_df = client._loader.get_table("dlp_lecivelatky")
    total_substances = len(substances_df) if substances_df is not None else 0

    # ATC hierarchy
    atc_df = client._loader.get_table("dlp_atc")
    atc_counts = {}
    if atc_df is not None:
        atc_counts = {
            "level_1": len(atc_df[atc_df["KOD"].str.len() == 1]),
            "level_2": len(atc_df[atc_df["KOD"].str.len() == 3]),
            "level_3": len(atc_df[atc_df["KOD"].str.len() == 4]),
            "level_4": len(atc_df[atc_df["KOD"].str.len() == 5]),
            "level_5": len(atc_df[atc_df["KOD"].str.len() == 7]),
        }

    # Pharmacies
    pharmacies_df = client._loader.get_table("lekarny_seznam")
    total_pharmacies = len(pharmacies_df) if pharmacies_df is not None else 0

    return {
        "medicines": {
            "total": total_medicines,
            "available": available_count,
            "unavailable": total_medicines - available_count,
        },
        "substances": {"total": total_substances},
        "atc_hierarchy": atc_counts,
        "pharmacies": {"total": total_pharmacies},
        "data_source": "SÚKL Open Data",
        "server_version": "4.1.0",
        "last_update": "2024-12-23",
    }


@mcp.resource("sukl://documents/{sukl_code}/availability")
async def get_document_availability(sukl_code: str) -> dict:
    """
    Lehká kontrola dostupnosti dokumentů (PIL/SPC) pro daný lék.

    Vrací informace o dostupnosti Příbalové informace (PIL) a Souhrnu
    údajů o přípravku (SPC) bez stahování a parsování dokumentů.

    Args:
        sukl_code: SÚKL kód léčivého přípravku (např. "0123456")

    Returns:
        Informace o dostupnosti PIL a SPC dokumentů s URL

    Examples:
        - sukl://documents/0123456/availability
        - sukl://documents/0234567/availability

    Note:
        - Lightweight check - nekontroluje skutečnou existenci souborů
        - Pro stažení obsahu použijte nástroje get_pil_content nebo get_spc_content
        - URL jsou standardizované podle SÚKL formátu
    """
    # Standardizované URL podle SÚKL konvence
    base_url = "https://prehledy.sukl.cz"

    return {
        "sukl_code": sukl_code,
        "pil": {
            "url": f"{base_url}/pil/{sukl_code}.pdf",
            "type": "Příbalová informace (PIL)",
            "format": "pdf",
            "description": "Informace pro pacienty v českém jazyce",
        },
        "spc": {
            "url": f"{base_url}/spc/{sukl_code}.pdf",
            "type": "Souhrn údajů o přípravku (SPC)",
            "format": "pdf",
            "description": "Odborné informace pro zdravotnické pracovníky",
        },
        "note": "Pro stažení a parsování obsahu použijte get_pil_content nebo get_spc_content",
    }


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
