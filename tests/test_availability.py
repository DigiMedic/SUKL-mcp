"""
Testy pro EPIC 4: Availability & Alternatives.

Testuje:
- Normalizaci dostupnosti (AvailabilityStatus)
- Parsování síly přípravku (_parse_strength)
- Výpočet podobnosti síly (_calculate_strength_similarity)
- Rankování alternativ (_rank_alternatives)
- Hlavní algoritmus hledání alternativ (find_generic_alternatives)
- Integraci check_availability() tool
"""

import pandas as pd
import pytest

from sukl_mcp.client_csv import SUKLClient
from sukl_mcp.models import AvailabilityStatus


# === Test Fixtures ===


@pytest.fixture
def sukl_client():
    """Vytvoř instanci SUKLClient pro testování."""
    return SUKLClient()


# === Normalization Tests (Step 1) ===


def test_normalize_availability_value_1(sukl_client):
    """Test normalizace hodnoty '1' → AVAILABLE."""
    result = sukl_client._normalize_availability("1")
    assert result == AvailabilityStatus.AVAILABLE


def test_normalize_availability_value_0(sukl_client):
    """Test normalizace hodnoty '0' → UNAVAILABLE."""
    result = sukl_client._normalize_availability("0")
    assert result == AvailabilityStatus.UNAVAILABLE


def test_normalize_availability_value_a(sukl_client):
    """Test normalizace hodnoty 'A' → AVAILABLE."""
    result = sukl_client._normalize_availability("A")
    assert result == AvailabilityStatus.AVAILABLE


def test_normalize_availability_value_n(sukl_client):
    """Test normalizace hodnoty 'N' → UNAVAILABLE."""
    result = sukl_client._normalize_availability("N")
    assert result == AvailabilityStatus.UNAVAILABLE


def test_normalize_availability_case_insensitive(sukl_client):
    """Test že normalizace je case-insensitive."""
    assert sukl_client._normalize_availability("a") == AvailabilityStatus.AVAILABLE
    assert sukl_client._normalize_availability("A") == AvailabilityStatus.AVAILABLE
    assert sukl_client._normalize_availability("ano") == AvailabilityStatus.AVAILABLE
    assert sukl_client._normalize_availability("ANO") == AvailabilityStatus.AVAILABLE


def test_normalize_availability_with_whitespace(sukl_client):
    """Test normalizace s mezerami."""
    assert sukl_client._normalize_availability("  1  ") == AvailabilityStatus.AVAILABLE
    assert sukl_client._normalize_availability("  0  ") == AvailabilityStatus.UNAVAILABLE


def test_normalize_availability_czech_values(sukl_client):
    """Test českých hodnot (ano/ne)."""
    assert sukl_client._normalize_availability("ano") == AvailabilityStatus.AVAILABLE
    assert sukl_client._normalize_availability("ne") == AvailabilityStatus.UNAVAILABLE


def test_normalize_availability_english_values(sukl_client):
    """Test anglických hodnot (yes/no)."""
    assert sukl_client._normalize_availability("yes") == AvailabilityStatus.AVAILABLE
    assert sukl_client._normalize_availability("no") == AvailabilityStatus.UNAVAILABLE


def test_normalize_availability_boolean_strings(sukl_client):
    """Test boolean string hodnot (true/false)."""
    assert sukl_client._normalize_availability("true") == AvailabilityStatus.AVAILABLE
    assert sukl_client._normalize_availability("false") == AvailabilityStatus.UNAVAILABLE


def test_normalize_availability_pandas_na(sukl_client):
    """Test pandas NA hodnoty → UNKNOWN."""
    result = sukl_client._normalize_availability(pd.NA)
    assert result == AvailabilityStatus.UNKNOWN


def test_normalize_availability_none(sukl_client):
    """Test None hodnoty → UNKNOWN."""
    result = sukl_client._normalize_availability(None)
    assert result == AvailabilityStatus.UNKNOWN


def test_normalize_availability_invalid_value(sukl_client):
    """Test neplatné hodnoty → UNKNOWN."""
    result = sukl_client._normalize_availability("invalid")
    assert result == AvailabilityStatus.UNKNOWN


def test_normalize_availability_empty_string(sukl_client):
    """Test prázdný string → UNKNOWN."""
    result = sukl_client._normalize_availability("")
    assert result == AvailabilityStatus.UNKNOWN


def test_normalize_availability_numeric_types(sukl_client):
    """Test numerických typů (integer/float)."""
    assert sukl_client._normalize_availability(1) == AvailabilityStatus.AVAILABLE
    assert sukl_client._normalize_availability(0) == AvailabilityStatus.UNAVAILABLE
    assert sukl_client._normalize_availability(1.0) == AvailabilityStatus.AVAILABLE
    assert sukl_client._normalize_availability(0.0) == AvailabilityStatus.UNAVAILABLE


# === Edge Cases ===


def test_normalize_availability_various_invalid_values(sukl_client):
    """Test různých neplatných hodnot → UNKNOWN."""
    invalid_values = ["X", "?", "999", "-1", "maybe", "unknown", "n/a"]

    for value in invalid_values:
        result = sukl_client._normalize_availability(value)
        assert result == AvailabilityStatus.UNKNOWN, f"Failed for value: {value}"


# === Strength Parsing Tests (Step 2) ===


def test_parse_strength_mg(sukl_client):
    """Test parsování miligramů (mg)."""
    value, unit = sukl_client._parse_strength("500mg")
    assert value == 500.0
    assert unit == "MG"


def test_parse_strength_mg_with_space(sukl_client):
    """Test parsování s mezerou mezi hodnotou a jednotkou."""
    value, unit = sukl_client._parse_strength("500 mg")
    assert value == 500.0
    assert unit == "MG"


def test_parse_strength_g_to_mg_conversion(sukl_client):
    """Test konverze gramů na miligramy (1g = 1000mg)."""
    value, unit = sukl_client._parse_strength("2g")
    assert value == 2000.0  # 2g = 2000mg
    assert unit == "MG"


def test_parse_strength_decimal_with_comma(sukl_client):
    """Test parsování s českou desetinnou čárkou."""
    value, unit = sukl_client._parse_strength("2,5g")
    assert value == 2500.0  # 2.5g = 2500mg
    assert unit == "MG"


def test_parse_strength_decimal_with_dot(sukl_client):
    """Test parsování s anglickou desetinnou tečkou."""
    value, unit = sukl_client._parse_strength("2.5g")
    assert value == 2500.0
    assert unit == "MG"


def test_parse_strength_ml(sukl_client):
    """Test parsování mililitrů (ml)."""
    value, unit = sukl_client._parse_strength("100ml")
    assert value == 100.0
    assert unit == "ML"


def test_parse_strength_percent(sukl_client):
    """Test parsování procent (%)."""
    value, unit = sukl_client._parse_strength("10%")
    assert value == 10.0
    assert unit == "%"


def test_parse_strength_iu(sukl_client):
    """Test parsování mezinárodních jednotek (IU)."""
    value, unit = sukl_client._parse_strength("1000iu")
    assert value == 1000.0
    assert unit == "IU"


def test_parse_strength_case_insensitive(sukl_client):
    """Test že parsování je case-insensitive."""
    value1, unit1 = sukl_client._parse_strength("500MG")
    value2, unit2 = sukl_client._parse_strength("500mg")
    assert value1 == value2 == 500.0
    assert unit1 == unit2 == "MG"


def test_parse_strength_number_only(sukl_client):
    """Test parsování pouze číselné hodnoty bez jednotky."""
    value, unit = sukl_client._parse_strength("500")
    assert value == 500.0
    assert unit == ""


def test_parse_strength_none(sukl_client):
    """Test parsování None hodnoty."""
    value, unit = sukl_client._parse_strength(None)
    assert value is None
    assert unit == ""


def test_parse_strength_empty_string(sukl_client):
    """Test parsování prázdného stringu."""
    value, unit = sukl_client._parse_strength("")
    assert value is None
    assert unit == ""


def test_parse_strength_pandas_na(sukl_client):
    """Test parsování pandas NA hodnoty."""
    value, unit = sukl_client._parse_strength(pd.NA)
    assert value is None
    assert unit == ""


def test_parse_strength_invalid(sukl_client):
    """Test parsování neplatného stringu."""
    value, unit = sukl_client._parse_strength("invalid")
    assert value is None
    assert unit == "invalid"


def test_parse_strength_complex_format(sukl_client):
    """Test parsování komplexního formátu (např. kombinace)."""
    # Parser by měl vzít první hodnotu
    value, unit = sukl_client._parse_strength("500mg/5ml")
    assert value == 500.0
    assert unit == "MG"


# === Strength Similarity Tests (Step 2) ===


def test_strength_similarity_identical(sukl_client):
    """Test identických sil → 1.0."""
    similarity = sukl_client._calculate_strength_similarity("500mg", "500mg")
    assert similarity == 1.0


def test_strength_similarity_same_unit_different_value(sukl_client):
    """Test stejná jednotka, různá hodnota."""
    similarity = sukl_client._calculate_strength_similarity("500mg", "1000mg")
    assert similarity == 0.5  # 500/1000 = 0.5


def test_strength_similarity_close_values(sukl_client):
    """Test podobných hodnot."""
    similarity = sukl_client._calculate_strength_similarity("900mg", "1000mg")
    assert similarity == 0.9  # 900/1000 = 0.9


def test_strength_similarity_different_units(sukl_client):
    """Test různých jednotek → nízká podobnost."""
    similarity = sukl_client._calculate_strength_similarity("500mg", "100ml")
    assert similarity == 0.3


def test_strength_similarity_g_vs_mg(sukl_client):
    """Test konverze g → mg při porovnání."""
    # 1g = 1000mg
    similarity = sukl_client._calculate_strength_similarity("1g", "1000mg")
    assert similarity == 1.0  # Po konverzi jsou identické


def test_strength_similarity_unparseable(sukl_client):
    """Test neparsovatených hodnot → 0.0."""
    similarity = sukl_client._calculate_strength_similarity("invalid", "something")
    assert similarity == 0.0


def test_strength_similarity_identical_strings(sukl_client):
    """Test identických stringů bez jednotek → 0.5."""
    similarity = sukl_client._calculate_strength_similarity("invalid", "invalid")
    assert similarity == 0.5


def test_strength_similarity_one_parseable_one_not(sukl_client):
    """Test kdy jedna hodnota je parsovatená, druhá ne → 0.0."""
    similarity = sukl_client._calculate_strength_similarity("500mg", "invalid")
    assert similarity == 0.0


def test_strength_similarity_none_values(sukl_client):
    """Test None hodnot → 0.0."""
    similarity = sukl_client._calculate_strength_similarity(None, "500mg")
    assert similarity == 0.0


def test_strength_similarity_empty_strings(sukl_client):
    """Test prázdných stringů → 0.0."""
    similarity = sukl_client._calculate_strength_similarity("", "")
    assert similarity == 0.0


# === Ranking Tests (Step 3) ===


def test_rank_alternatives_by_form(sukl_client):
    """Test rankování podle formy (40 bodů)."""
    original = {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "PARALEN", "max_price": 100.0}

    candidates = [
        {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "PARALEN 500", "max_price": 90.0},
        {"FORMA": "sirup", "SILA": "500mg", "NAZEV": "PARALEN SIRUP", "max_price": 90.0},
    ]

    ranked = sukl_client._rank_alternatives(candidates, original)

    # Tableta by měla být první (forma match = 40 bodů)
    assert ranked[0]["FORMA"] == "tableta"
    assert ranked[0]["relevance_score"] > ranked[1]["relevance_score"]


def test_rank_alternatives_by_strength(sukl_client):
    """Test rankování podle síly (30 bodů)."""
    original = {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "PARALEN", "max_price": 100.0}

    candidates = [
        {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "A", "max_price": 100.0},  # Identická síla
        {"FORMA": "tableta", "SILA": "1000mg", "NAZEV": "B", "max_price": 100.0},  # Jiná síla
    ]

    ranked = sukl_client._rank_alternatives(candidates, original)

    # 500mg by mělo být první (lepší strength similarity)
    assert ranked[0]["SILA"] == "500mg"
    assert ranked[0]["relevance_score"] > ranked[1]["relevance_score"]


def test_rank_alternatives_by_price(sukl_client):
    """Test rankování podle ceny (20 bodů)."""
    original = {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "PARALEN", "max_price": 100.0}

    candidates = [
        {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "A", "max_price": 80.0},  # Levnější
        {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "B", "max_price": 120.0},  # Dražší
    ]

    ranked = sukl_client._rank_alternatives(candidates, original)

    # Levnější by měl být první
    assert ranked[0]["max_price"] == 80.0
    assert ranked[0]["relevance_score"] > ranked[1]["relevance_score"]


def test_rank_alternatives_by_name(sukl_client):
    """Test rankování podle názvu (10 bodů)."""
    original = {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "PARALEN 500", "max_price": None}

    candidates = [
        {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "PARALEN 500MG", "max_price": None},
        {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "ZCELA JINÝ NÁZEV", "max_price": None},
    ]

    ranked = sukl_client._rank_alternatives(candidates, original)

    # PARALEN 500MG by měl být první (podobný název)
    assert "PARALEN" in ranked[0]["NAZEV"]
    assert ranked[0]["relevance_score"] > ranked[1]["relevance_score"]


def test_rank_alternatives_complete_scoring(sukl_client):
    """Test kompletního skórovacího systému."""
    original = {
        "FORMA": "tableta",
        "SILA": "500mg",
        "NAZEV": "PARALEN 500",
        "max_price": 100.0,
    }

    candidates = [
        {
            "FORMA": "tableta",  # +40
            "SILA": "500mg",  # +30 (identická)
            "NAZEV": "PARALEN 500MG",  # ~+9-10 (high similarity)
            "max_price": 90.0,  # +20 (levnější)
        },  # Total: ~99-100
        {
            "FORMA": "sirup",  # +0
            "SILA": "1000mg",  # +15 (0.5 similarity)
            "NAZEV": "JINÝ LÉK",  # ~+1-2 (low similarity)
            "max_price": 150.0,  # ~+13 (dražší, ratio 0.67)
        },  # Total: ~29-30
    ]

    ranked = sukl_client._rank_alternatives(candidates, original)

    # První by měl mít skóre blízké 100
    assert ranked[0]["FORMA"] == "tableta"
    assert ranked[0]["relevance_score"] > 90.0

    # Druhý by měl mít mnohem nižší skóre
    assert ranked[1]["FORMA"] == "sirup"
    assert ranked[1]["relevance_score"] < 40.0


def test_rank_alternatives_missing_data(sukl_client):
    """Test s chybějícími daty."""
    original = {"FORMA": "tableta", "NAZEV": "PARALEN"}

    candidates = [
        {"FORMA": "tableta", "NAZEV": "PARALEN 500"},
        {"NAZEV": "JINÝ"},  # Chybí FORMA
    ]

    ranked = sukl_client._rank_alternatives(candidates, original)

    # Mělo by fungovat i s chybějícími daty
    assert len(ranked) == 2
    assert all("relevance_score" in c for c in ranked)


def test_rank_alternatives_empty_list(sukl_client):
    """Test s prázdným seznamem kandidátů."""
    original = {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "PARALEN"}

    ranked = sukl_client._rank_alternatives([], original)

    assert ranked == []


def test_rank_alternatives_partial_form_match(sukl_client):
    """Test částečné shody formy (např. 'tableta' vs 'tableta obalená')."""
    original = {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "A", "max_price": 100.0}

    candidates = [
        {"FORMA": "tableta obalená", "SILA": "500mg", "NAZEV": "B", "max_price": 100.0},
        {"FORMA": "sirup", "SILA": "500mg", "NAZEV": "C", "max_price": 100.0},
    ]

    ranked = sukl_client._rank_alternatives(candidates, original)

    # "tableta obalená" by měla dostat částečné body (20)
    assert ranked[0]["FORMA"] == "tableta obalená"
    # Měla by mít vyšší skóre než "sirup"
    assert ranked[0]["relevance_score"] > ranked[1]["relevance_score"]


def test_rank_alternatives_preserves_order_for_same_score(sukl_client):
    """Test že při stejném skóre je zachováno pořadí."""
    original = {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "A"}

    candidates = [
        {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "B"},
        {"FORMA": "tableta", "SILA": "500mg", "NAZEV": "C"},
    ]

    ranked = sukl_client._rank_alternatives(candidates, original)

    # Oba by měli mít stejné nebo velmi podobné skóre
    assert abs(ranked[0]["relevance_score"] - ranked[1]["relevance_score"]) < 1.0
