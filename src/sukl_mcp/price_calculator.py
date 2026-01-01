"""
Cenová logika pro SÚKL léčivé přípravky.

Implementuje práci s dlp_cau.csv (Cenové a úhradové údaje) včetně:
- Získání cenových údajů pro konkrétní léčivo
- Kalkulace doplatku pacienta
- Filtrování podle platnosti
- Zpracování různých formátů sloupců
"""

import logging
from datetime import date, datetime
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


# === Column Name Mapping ===
# Podporujeme různé varianty názvů sloupců z dlp_cau.csv

# KOD_SUKL variants
SUKL_CODE_COLUMNS = ["KOD_SUKL", "kod_sukl", "SUKL_CODE"]

# Maximální cena variants
MAX_PRICE_COLUMNS = ["MC", "CENA_MAX", "MAX_CENA", "MAX_PRICE"]

# Úhrada pojišťovny variants
REIMBURSEMENT_COLUMNS = ["UHR1", "UHRADA", "REIMBURSEMENT", "UHRADA_1"]

# Doplatek pacienta variants (pokud existuje přímo v CSV)
COPAY_COLUMNS = ["DOPLATEK", "COPAY", "DOPLATEK_PACIENTA"]

# Platnost do variants
VALIDITY_COLUMNS = ["PLATNOST_DO", "DATUM_DO", "VALID_UNTIL"]

# Indikační skupina variants
INDICATION_GROUP_COLUMNS = ["IND_SK", "INDIKACNI_SKUPINA", "INDICATION_GROUP"]


# === Helper Functions ===


def _find_column(df: pd.DataFrame, variants: list[str]) -> Optional[str]:
    """
    Najdi sloupec z variantních názvů.

    Args:
        df: DataFrame pro hledání
        variants: Seznam možných názvů sloupce

    Returns:
        První nalezený název sloupce nebo None
    """
    for variant in variants:
        if variant in df.columns:
            return variant
    return None


def _get_numeric_value(value: Any) -> Optional[float]:
    """
    Konverze hodnoty na float, s graceful handling.

    Args:
        value: Hodnota pro konverzi

    Returns:
        Float hodnota nebo None
    """
    if pd.isna(value):
        return None

    try:
        # Pokud je to string, odstraň čárky (české tisícovky)
        if isinstance(value, str):
            value = value.replace(",", ".").replace(" ", "")
        return float(value)
    except (ValueError, TypeError):
        return None


def _parse_date(value: Any) -> Optional[date]:
    """
    Parse datum z různých formátů.

    Args:
        value: Hodnota pro parsing

    Returns:
        date objekt nebo None
    """
    if pd.isna(value):
        return None

    try:
        # Důležité: datetime musí být kontrolován PŘED date (datetime je podtřída date)
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        # Parse string formáty (DD.MM.YYYY, YYYY-MM-DD, atd.)
        if isinstance(value, str):
            # Zkus několik běžných formátů
            for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"]:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

        return None
    except Exception:
        return None


# === Price Data Functions ===


def get_price_data(
    df_cau: pd.DataFrame,
    sukl_code: str,
    reference_date: Optional[date] = None,
) -> Optional[dict[str, Any]]:
    """
    Získej cenová data pro konkrétní léčivo.

    Args:
        df_cau: DataFrame s cenovými daty (dlp_cau)
        sukl_code: SÚKL kód léčiva
        reference_date: Referenční datum pro kontrolu platnosti (default: dnes)

    Returns:
        Dict s cenovými údaji nebo None
    """
    if df_cau is None or df_cau.empty:
        return None

    if reference_date is None:
        reference_date = date.today()

    # Najdi sloupce
    col_sukl = _find_column(df_cau, SUKL_CODE_COLUMNS)
    col_max_price = _find_column(df_cau, MAX_PRICE_COLUMNS)
    col_reimbursement = _find_column(df_cau, REIMBURSEMENT_COLUMNS)
    col_copay = _find_column(df_cau, COPAY_COLUMNS)
    col_validity = _find_column(df_cau, VALIDITY_COLUMNS)
    col_indication = _find_column(df_cau, INDICATION_GROUP_COLUMNS)

    if col_sukl is None:
        logger.warning("dlp_cau neobsahuje sloupec KOD_SUKL")
        return None

    # Normalizuj SÚKL kód (odstranění nul na začátku)
    sukl_code_normalized = str(int(sukl_code)) if sukl_code.isdigit() else sukl_code

    # Filtruj podle SÚKL kódu
    mask = df_cau[col_sukl].astype(str) == sukl_code_normalized
    records = df_cau[mask]

    if records.empty:
        return None

    # Filtruj podle platnosti (pokud existuje sloupec)
    if col_validity:
        valid_records = []
        for _, row in records.iterrows():
            validity_date = _parse_date(row[col_validity])
            if validity_date is None or validity_date >= reference_date:
                valid_records.append(row)

        if not valid_records:
            return None

        # Vyber nejnovější platný záznam (podle validity nebo poslední v seznamu)
        record = valid_records[-1] if valid_records else None
    else:
        # Pokud není sloupec validity, vyber poslední záznam
        record = records.iloc[-1]

    if record is None:
        return None

    # Extrahuj cenové údaje
    max_price = _get_numeric_value(record[col_max_price]) if col_max_price else None
    reimbursement = (
        _get_numeric_value(record[col_reimbursement]) if col_reimbursement else None
    )
    copay = _get_numeric_value(record[col_copay]) if col_copay else None

    # Vypočítej doplatek, pokud není přímo v CSV
    if copay is None and max_price is not None and reimbursement is not None:
        copay = max(0.0, max_price - reimbursement)

    # Sestavení výsledku
    result = {
        "sukl_code": sukl_code,
        "max_price": max_price,
        "reimbursement_amount": reimbursement,
        "patient_copay": copay,
        "is_reimbursed": reimbursement is not None and reimbursement > 0,
    }

    # Přidej indikační skupinu (pokud existuje)
    if col_indication:
        result["indication_group"] = record[col_indication]

    # Přidej platnost (pokud existuje)
    if col_validity:
        validity_date = _parse_date(record[col_validity])
        if validity_date:
            result["valid_until"] = validity_date.isoformat()

    return result


def calculate_patient_copay(max_price: float, reimbursement: float) -> float:
    """
    Vypočítej doplatek pacienta.

    Args:
        max_price: Maximální cena přípravku
        reimbursement: Výše úhrady pojišťovny

    Returns:
        Doplatek pacienta (vždy >= 0)
    """
    return max(0.0, max_price - reimbursement)


def has_reimbursement(df_cau: pd.DataFrame, sukl_code: str) -> bool:
    """
    Zkontroluj zda má přípravek úhradu pojišťovny.

    Args:
        df_cau: DataFrame s cenovými daty
        sukl_code: SÚKL kód léčiva

    Returns:
        True pokud má úhradu, False jinak
    """
    price_data = get_price_data(df_cau, sukl_code)
    return price_data is not None and price_data.get("is_reimbursed", False)


def get_reimbursement_amount(df_cau: pd.DataFrame, sukl_code: str) -> Optional[float]:
    """
    Získej výši úhrady pojišťovny.

    Args:
        df_cau: DataFrame s cenovými daty
        sukl_code: SÚKL kód léčiva

    Returns:
        Výše úhrady nebo None
    """
    price_data = get_price_data(df_cau, sukl_code)
    return price_data.get("reimbursement_amount") if price_data else None
