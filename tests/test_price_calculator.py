"""
Testy pro cenovou logiku (price_calculator.py).

Testuje:
- Mapování názvů sloupců
- Konverze numerických hodnot
- Parsování datumů
- Získání cenových dat
- Kalkulaci doplatku pacienta
"""

from datetime import date, datetime

import pandas as pd
import pytest

from sukl_mcp.price_calculator import (
    _find_column,
    _get_numeric_value,
    _parse_date,
    calculate_patient_copay,
    get_price_data,
    get_reimbursement_amount,
    has_reimbursement,
)

# === Test Fixtures ===


@pytest.fixture
def sample_cau_df():
    """Vzorový dlp_cau DataFrame s cenovými daty."""
    return pd.DataFrame(
        {
            "KOD_SUKL": ["12345", "67890", "11111"],
            "MC": [150.50, 89.90, 250.00],  # Maximální cena
            "UHR1": [100.00, 89.90, 0.00],  # Úhrada pojišťovny
            "IND_SK": ["A", "B", None],  # Indikační skupina
            "PLATNOST_DO": [
                "31.12.2026",
                "01.01.2027",
                "31.12.2027",
            ],  # Všechny platné v budoucnosti
        }
    )


@pytest.fixture
def alternative_column_names_df():
    """DataFrame s alternativními názvy sloupců."""
    return pd.DataFrame(
        {
            "kod_sukl": ["12345"],
            "CENA_MAX": [150.50],
            "UHRADA": [100.00],
            "INDIKACNI_SKUPINA": ["A"],
            "DATUM_DO": ["31.12.2026"],
        }
    )


# === Column Mapping Tests ===


def test_find_column_first_variant():
    """Test nalezení sloupce - první varianta."""
    df = pd.DataFrame({"KOD_SUKL": [1, 2, 3], "OTHER": [4, 5, 6]})
    variants = ["KOD_SUKL", "kod_sukl", "SUKL_CODE"]
    assert _find_column(df, variants) == "KOD_SUKL"


def test_find_column_second_variant():
    """Test nalezení sloupce - druhá varianta."""
    df = pd.DataFrame({"kod_sukl": [1, 2, 3], "OTHER": [4, 5, 6]})
    variants = ["KOD_SUKL", "kod_sukl", "SUKL_CODE"]
    assert _find_column(df, variants) == "kod_sukl"


def test_find_column_not_found():
    """Test když sloupec není nalezen."""
    df = pd.DataFrame({"OTHER": [1, 2, 3]})
    variants = ["KOD_SUKL", "kod_sukl", "SUKL_CODE"]
    assert _find_column(df, variants) is None


# === Numeric Conversion Tests ===


def test_get_numeric_value_int():
    """Test konverze integer."""
    assert _get_numeric_value(123) == 123.0


def test_get_numeric_value_float():
    """Test konverze float."""
    assert _get_numeric_value(123.45) == 123.45


def test_get_numeric_value_string():
    """Test konverze string s číslem."""
    assert _get_numeric_value("123.45") == 123.45


def test_get_numeric_value_string_with_comma():
    """Test konverze string s čárkou (české formátování)."""
    assert _get_numeric_value("123,45") == 123.45


def test_get_numeric_value_string_with_spaces():
    """Test konverze string s mezerami."""
    assert _get_numeric_value("123 456.78") == 123456.78


def test_get_numeric_value_na():
    """Test konverze NaN hodnoty."""
    assert _get_numeric_value(pd.NA) is None


def test_get_numeric_value_none():
    """Test konverze None."""
    assert _get_numeric_value(None) is None


def test_get_numeric_value_invalid_string():
    """Test konverze neplatného stringu."""
    assert _get_numeric_value("invalid") is None


# === Date Parsing Tests ===


def test_parse_date_date_object():
    """Test parsování date objektu."""
    d = date(2025, 12, 31)
    assert _parse_date(d) == d


def test_parse_date_datetime_object():
    """Test parsování datetime objektu."""
    dt = datetime(2025, 12, 31, 10, 30)
    assert _parse_date(dt) == date(2025, 12, 31)


def test_parse_date_string_ddmmyyyy():
    """Test parsování string DD.MM.YYYY."""
    assert _parse_date("31.12.2025") == date(2025, 12, 31)


def test_parse_date_string_yyyymmdd():
    """Test parsování string YYYY-MM-DD."""
    assert _parse_date("2025-12-31") == date(2025, 12, 31)


def test_parse_date_string_ddmmyyyy_slash():
    """Test parsování string DD/MM/YYYY."""
    assert _parse_date("31/12/2025") == date(2025, 12, 31)


def test_parse_date_na():
    """Test parsování NaN hodnoty."""
    assert _parse_date(pd.NA) is None


def test_parse_date_none():
    """Test parsování None."""
    assert _parse_date(None) is None


def test_parse_date_invalid_string():
    """Test parsování neplatného datumu."""
    assert _parse_date("invalid") is None


# === Price Data Tests ===


def test_get_price_data_success(sample_cau_df):
    """Test úspěšného získání cenových dat."""
    # Použij explicitní reference_date aby test byl deterministický
    result = get_price_data(sample_cau_df, "12345", reference_date=date(2025, 12, 1))

    assert result is not None
    assert result["sukl_code"] == "12345"
    assert result["max_price"] == 150.50
    assert result["reimbursement_amount"] == 100.00
    assert result["patient_copay"] == 50.50  # 150.50 - 100.00
    assert result["is_reimbursed"] is True
    assert result["indication_group"] == "A"


def test_get_price_data_no_reimbursement(sample_cau_df):
    """Test pro léčivo bez úhrady."""
    result = get_price_data(sample_cau_df, "11111")

    assert result is not None
    assert result["sukl_code"] == "11111"
    assert result["max_price"] == 250.00
    assert result["reimbursement_amount"] == 0.00
    assert result["patient_copay"] == 250.00  # Plná cena
    assert result["is_reimbursed"] is False


def test_get_price_data_full_reimbursement(sample_cau_df):
    """Test pro léčivo s plnou úhradou."""
    result = get_price_data(sample_cau_df, "67890")

    assert result is not None
    assert result["patient_copay"] == 0.00  # Plně hrazeno


def test_get_price_data_not_found(sample_cau_df):
    """Test pro neexistující SÚKL kód."""
    result = get_price_data(sample_cau_df, "99999")
    assert result is None


def test_get_price_data_empty_df():
    """Test s prázdným DataFrame."""
    df = pd.DataFrame()
    result = get_price_data(df, "12345")
    assert result is None


def test_get_price_data_none_df():
    """Test s None DataFrame."""
    result = get_price_data(None, "12345")
    assert result is None


def test_get_price_data_alternative_columns(alternative_column_names_df):
    """Test s alternativními názvy sloupců."""
    result = get_price_data(alternative_column_names_df, "12345", reference_date=date(2025, 12, 1))

    assert result is not None
    assert result["sukl_code"] == "12345"
    assert result["max_price"] == 150.50
    assert result["reimbursement_amount"] == 100.00
    assert result["patient_copay"] == 50.50


def test_get_price_data_validity_filter():
    """Test filtrace podle platnosti."""
    # Vytvoř DataFrame s neplatným záznamem
    df = pd.DataFrame(
        {
            "KOD_SUKL": ["11111"],
            "MC": [250.00],
            "UHR1": [0.00],
            "PLATNOST_DO": ["31.12.2024"],  # Minulost
        }
    )
    # Test s datem v budoucnosti - záznam by měl být filtrován
    result = get_price_data(df, "11111", reference_date=date(2025, 1, 1))
    # Mělo by vrátit None protože záznam je neplatný
    assert result is None


def test_get_price_data_validity_current(sample_cau_df):
    """Test s aktuálně platným záznamem."""
    result = get_price_data(sample_cau_df, "12345", reference_date=date(2025, 6, 1))
    assert result is not None
    assert result["sukl_code"] == "12345"


def test_get_price_data_with_validity_field(sample_cau_df):
    """Test že výsledek obsahuje valid_until pokud je k dispozici."""
    result = get_price_data(sample_cau_df, "12345", reference_date=date(2025, 12, 1))
    assert "valid_until" in result
    assert result["valid_until"] == "2026-12-31"


def test_get_price_data_missing_sukl_column():
    """Test když DataFrame nemá sloupec KOD_SUKL."""
    df = pd.DataFrame({"MC": [100.0], "UHR1": [50.0]})
    result = get_price_data(df, "12345")
    assert result is None


# === Patient Copay Tests ===


def test_calculate_patient_copay_positive():
    """Test výpočtu doplatku - pozitivní hodnota."""
    assert calculate_patient_copay(150.00, 100.00) == 50.00


def test_calculate_patient_copay_zero():
    """Test výpočtu doplatku - nulový doplatek."""
    assert calculate_patient_copay(100.00, 100.00) == 0.00


def test_calculate_patient_copay_negative_clamped():
    """Test výpočtu doplatku - záporná hodnota (clampnuto na 0)."""
    assert calculate_patient_copay(100.00, 150.00) == 0.00


def test_calculate_patient_copay_float_precision():
    """Test výpočtu doplatku - floating point precision."""
    result = calculate_patient_copay(150.50, 100.25)
    assert abs(result - 50.25) < 0.01


# === Helper Function Tests ===


def test_has_reimbursement_true(sample_cau_df):
    """Test has_reimbursement - léčivo s úhradou."""
    assert has_reimbursement(sample_cau_df, "12345") is True


def test_has_reimbursement_false(sample_cau_df):
    """Test has_reimbursement - léčivo bez úhrady."""
    assert has_reimbursement(sample_cau_df, "11111") is False


def test_has_reimbursement_not_found(sample_cau_df):
    """Test has_reimbursement - neexistující léčivo."""
    assert has_reimbursement(sample_cau_df, "99999") is False


def test_get_reimbursement_amount_success(sample_cau_df):
    """Test get_reimbursement_amount - úspěšné získání."""
    amount = get_reimbursement_amount(sample_cau_df, "12345")
    assert amount == 100.00


def test_get_reimbursement_amount_zero(sample_cau_df):
    """Test get_reimbursement_amount - nulová úhrada."""
    amount = get_reimbursement_amount(sample_cau_df, "11111")
    assert amount == 0.00


def test_get_reimbursement_amount_not_found(sample_cau_df):
    """Test get_reimbursement_amount - neexistující léčivo."""
    amount = get_reimbursement_amount(sample_cau_df, "99999")
    assert amount is None


# === Edge Cases Tests ===


def test_get_price_data_leading_zeros():
    """Test s SÚKL kódem s nulami na začátku."""
    df = pd.DataFrame(
        {
            "KOD_SUKL": ["123"],  # Normalizováno bez nul
            "MC": [100.0],
            "UHR1": [50.0],
        }
    )
    # Mělo by najít i když zadáme s nulami
    result = get_price_data(df, "00123")
    assert result is not None
    assert result["sukl_code"] == "00123"


def test_get_price_data_multiple_records_uses_latest():
    """Test že při více záznamech se použije poslední."""
    df = pd.DataFrame(
        {
            "KOD_SUKL": ["12345", "12345"],  # Duplikát
            "MC": [100.0, 150.0],  # Různé ceny
            "UHR1": [50.0, 100.0],
            "PLATNOST_DO": ["31.12.2025", "31.12.2026"],  # Druhý je novější
        }
    )
    result = get_price_data(df, "12345", reference_date=date(2025, 12, 1))
    assert result is not None
    # Mělo by použít druhý záznam (novější platnost)
    assert result["max_price"] == 150.0


def test_get_price_data_missing_optional_columns():
    """Test s minimální sadou sloupců."""
    df = pd.DataFrame(
        {
            "KOD_SUKL": ["12345"],
            "MC": [150.0],
            "UHR1": [100.0],
            # Chybí IND_SK a PLATNOST_DO
        }
    )
    result = get_price_data(df, "12345")
    assert result is not None
    assert "indication_group" not in result
    assert "valid_until" not in result


# === Integration Tests ===


def test_price_enrichment_workflow(sample_cau_df):
    """
    Integrační test - simuluje workflow obohacení výsledků vyhledávání.
    """
    # Simuluj výsledky vyhledávání
    search_results = [
        {"KOD_SUKL": "12345", "NAZEV": "Léčivo A"},
        {"KOD_SUKL": "67890", "NAZEV": "Léčivo B"},
        {"KOD_SUKL": "99999", "NAZEV": "Léčivo C"},  # Nemá cenová data
    ]

    # Obohať výsledky o cenové údaje
    for result in search_results:
        sukl_code = str(result["KOD_SUKL"])
        price_data = get_price_data(sample_cau_df, sukl_code, reference_date=date(2025, 12, 1))

        if price_data:
            result["has_reimbursement"] = price_data["is_reimbursed"]
            result["max_price"] = price_data["max_price"]
            result["patient_copay"] = price_data["patient_copay"]
        else:
            result["has_reimbursement"] = False
            result["max_price"] = None
            result["patient_copay"] = None

    # Ověř výsledky
    assert search_results[0]["has_reimbursement"] is True
    assert search_results[0]["max_price"] == 150.50
    assert search_results[0]["patient_copay"] == 50.50

    assert search_results[1]["has_reimbursement"] is True
    assert search_results[1]["patient_copay"] == 0.00  # Plně hrazeno

    assert search_results[2]["has_reimbursement"] is False
    assert search_results[2]["max_price"] is None
