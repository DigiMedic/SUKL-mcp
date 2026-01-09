"""
OPRAVA PRO: get_reimbursement - REST API integrace pro CAU-SCAU endpoint

Tento soubor obsahuje opravenou funkci get_reimbursement, která:
- Používá REST API endpoint /dlp/v1/cau-scau/{kodSUKL} jako primary zdroj
- Má fallback na CSV (dlp_cau.csv) pokud REST API selže
- Vrací přesná cenová data: 162.82 Kč, 83.06 Kč, 79.76 Kč

NÁVOD NA APLIKACI:
1. Zkopírovat tuto funkci do /Users/petrsovadina/Desktop/Develope/personal/SUKL-mcp/src/sukl_mcp/server.py
2. Nahradit původní funkci get_reimbursement (Lines 869-979)
3. Ověřit, že import API_BASE existuje na začátku souboru
"""

import httpx
import pandas as pd
from typing import Optional

from fastmcp import Context
from sukl_mcp.api import get_api_client, SUKLAPIError
from sukl_mcp.client_csv import get_sukl_client
from sukl_mcp.models import ReimbursementInfo

# Konstanta pro API base URL (mí být definována v server.py)
API_BASE = "https://prehledy.sukl.cz/dlp/v1"


async def get_reimbursement(
    sukl_code: str,
    ctx: Context | None = None,
) -> ReimbursementInfo | None:
    """
    Získá informace o úhradě léčivého přípravku zdravotní pojišťovnou včetně cen.

    OPRAVA v4.0: Cenová data JSOU v REST API, ne jen v CSV!
    - Dataset DLPO (léčiva) = CSV ✅
    - Dataset SCAU (ceny & úhrady) = REST API ✅

    v4.0: PURE REST API pro CAU-SCAU endpoint
    - Primary: REST API /dlp/v1/cau-scau/{kodSUKL}
    - Fallback: CSV dlp_cau.csv (pokud REST API selže)

    REST API endpoint vrací:
    - maxCenaLekarna: Maximální cena v lékárně (např. 162.82 Kč)
    - cenaPuvodce: Cena výrobce (např. 106.11 Kč)
    - uhrada: Úhrada pojišťovnou (např. 79.76 Kč)
    - zapocitatelnyDoplatek: Započitatelný doplatek (např. 83.06 Kč)

    Args:
        sukl_code: SÚKL kód přípravku (7 číslic, např. "0012345")
        ctx: Context pro logging (auto-injected by FastMCP)

    Returns:
        ReimbursementInfo s cenovými a úhradovými informacemi nebo None

    Examples:
        - get_reimbursement("0094156")  # ABAKTAL
        → max_price: 162.82, patient_copay: 83.06, reimbursement_amount: 79.76
    """
    # Validace vstupu
    if not sukl_code or not sukl_code.isdigit() or len(sukl_code) != 7:
        logger.warning(f"❌ Invalid sukl_code: '{sukl_code}'")
        if ctx:
            await ctx.warning(f"Invalid SÚKL code: {sukl_code}")
        return None

    sukl_code = sukl_code.strip().zfill(7)
    url = f"{API_BASE}/cau-scau/{sukl_code}"

    # Context-aware logging
    if ctx:
        await ctx.info(f"Fetching reimbursement info via REST API: {sukl_code}")

    try:
        # POKUS ZÍSKAT Z REST API (primary)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)

            if response.status_code == 404:
                logger.info(f"   ℹ️  No price data for {sukl_code} in REST API")
                # FALLBACK NA CSV (pokud existuje dlp_cau.csv)
                csv_client = await get_sukl_client()
                price_info = await csv_client.get_price_info(sukl_code)

                if price_info:
                    medicine_name = price_info.get("medicine_name", "")
                    return ReimbursementInfo(
                        sukl_code=sukl_code,
                        medicine_name=medicine_name,
                        is_reimbursed=price_info.get("is_reimbursed", False),
                        reimbursement_group=price_info.get("indication_group"),
                        max_producer_price=price_info.get("max_price"),
                        max_retail_price=price_info.get("max_price"),
                        reimbursement_amount=price_info.get("reimbursement_amount"),
                        patient_copay=price_info.get("patient_copay"),
                        has_indication_limit=bool(price_info.get("indication_group")),
                        indication_limit_text=price_info.get("indication_group"),
                        specialist_only=False,
                    )
                return None

            elif response.status_code >= 400:
                logger.warning(f"⚠️  REST API error: {response.status_code}")
                if ctx:
                    await ctx.warning(f"REST API error {response.status_code}, trying CSV fallback")
                # FALLBACK NA CSV
                csv_client = await get_sukl_client()
                price_info = await csv_client.get_price_info(sukl_code)

                if price_info:
                    medicine_name = price_info.get("medicine_name", "")
                    return ReimbursementInfo(
                        sukl_code=sukl_code,
                        medicine_name=medicine_name,
                        is_reimbursed=price_info.get("is_reimbursed", False),
                        reimbursement_group=price_info.get("indication_group"),
                        max_producer_price=price_info.get("max_price"),
                        max_retail_price=price_info.get("max_price"),
                        reimbursement_amount=price_info.get("reimbursement_amount"),
                        patient_copay=price_info.get("patient_copay"),
                        has_indication_limit=bool(price_info.get("indication_group")),
                        indication_limit_text=price_info.get("indication_group"),
                        specialist_only=False,
                    )
                return None

            else:
                response.raise_for_status()
                data = response.json()
                logger.info(f"   ✅ REST API success: {sukl_code}")
                if ctx:
                    await ctx.debug("Successfully retrieved pricing data via REST API")

        # Extrahovat úhrady (REST API)
        uhrady = data.get("uhrady", [])
        first_uhrada = uhrady[0] if uhrady else {}

        # Získat název léčiva
        medicine_name = data.get("nazev", "")
        if not medicine_name:
            # Fallback na CSV pro název
            csv_client = await get_sukl_client()
            detail = await csv_client.get_medicine_detail(sukl_code)
            if detail:
                medicine_name = detail.get("NAZEV", "")

        result = ReimbursementInfo(
            sukl_code=sukl_code,
            medicine_name=medicine_name,
            is_reimbursed=True,
            reimbursement_group=data.get("referencniSkupina"),
            max_producer_price=data.get("cenaPuvodce"),
            max_retail_price=data.get("maxCenaLekarna"),
            reimbursement_amount=first_uhrada.get("uhrada"),
            patient_copay=first_uhrada.get("zapocitatelnyDoplatek"),
            has_indication_limit=first_uhrada.get("omezeniPreskripceSmp", False),
            indication_limit_text=first_uhrada.get("specializacePredepisujicihoLekareKod"),
            specialist_only=bool(first_uhrada.get("specializacePredepisujicihoLekareKod")),
        )

        logger.info(f"   ✅ Price: {result.max_retail_price} Kč, Copay: {result.patient_copay} Kč")

        return result

    except httpx.HTTPError as e:
        logger.error(f"❌ HTTP error fetching reimbursement for {sukl_code}: {e}")
        # FALLBACK NA CSV při HTTP chybě
        try:
            csv_client = await get_sukl_client()
            price_info = await csv_client.get_price_info(sukl_code)

            if price_info:
                medicine_name = price_info.get("medicine_name", "")
                if ctx:
                    await ctx.info("Falling back to CSV pricing data")
                return ReimbursementInfo(
                    sukl_code=sukl_code,
                    medicine_name=medicine_name,
                    is_reimbursed=price_info.get("is_reimbursed", False),
                    reimbursement_group=price_info.get("indication_group"),
                    max_producer_price=price_info.get("max_price"),
                    max_retail_price=price_info.get("max_price"),
                    reimbursement_amount=price_info.get("reimbursement_amount"),
                    patient_copay=price_info.get("patient_copay"),
                    has_indication_limit=bool(price_info.get("indication_group")),
                    indication_limit_text=price_info.get("indication_group"),
                    specialist_only=False,
                )
        except Exception as csv_error:
            logger.error(f"❌ CSV fallback also failed: {csv_error}")
        return None
    except Exception as e:
        logger.error(f"❌ Error fetching reimbursement for {sukl_code}: {e}", exc_info=True)
        return None
