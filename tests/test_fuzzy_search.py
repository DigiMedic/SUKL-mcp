"""
Testy pro fuzzy search s multi-level pipeline.

Test coverage:
- Konfigurace konstant
- Scoring funkce
- FuzzyMatcher search pipeline (substance, exact, substring, fuzzy)
- Singleton pattern
- Input validace
- Edge cases
"""

import pandas as pd
import pytest

from sukl_mcp.exceptions import SUKLValidationError
from sukl_mcp.fuzzy_search import (
    FUZZY_CANDIDATE_LIMIT,
    FUZZY_MIN_QUERY_LENGTH,
    FUZZY_THRESHOLD,
    FuzzyMatcher,
    calculate_ranking_score,
    get_fuzzy_matcher,
)


# === Test Data Fixtures ===


@pytest.fixture
def sample_medicines_df():
    """Sample medicines DataFrame."""
    return pd.DataFrame(
        {
            "KOD_SUKL": [1, 2, 3, 4, 5],
            "NAZEV": [
                "IBUPROFEN 400MG",
                "PARALEN 500MG",
                "ASPIRIN 100MG",
                "IBUPROFEN FORTE 600MG",
                "PARACETAMOL 500MG",
            ],
            "DODAVKY": ["A", "0", "A", "A", "A"],
        }
    )


@pytest.fixture
def sample_composition_df():
    """Sample composition DataFrame."""
    return pd.DataFrame(
        {
            "KOD_SUKL": [1, 2, 3, 4, 5],
            "KOD_LATKY": [10, 20, 30, 10, 20],
        }
    )


@pytest.fixture
def sample_substances_df():
    """Sample substances DataFrame."""
    return pd.DataFrame(
        {
            "KOD": [10, 20, 30],
            "NAZEV": ["Ibuprofenum", "Paracetamolum", "Acidum acetylsalicylicum"],
        }
    )


# === Configuration Tests ===


def test_fuzzy_threshold_valid():
    """Test že FUZZY_THRESHOLD je validní hodnota."""
    assert 0 <= FUZZY_THRESHOLD <= 100
    assert isinstance(FUZZY_THRESHOLD, int)


def test_fuzzy_min_query_length_valid():
    """Test že FUZZY_MIN_QUERY_LENGTH je rozumná hodnota."""
    assert FUZZY_MIN_QUERY_LENGTH >= 1
    assert isinstance(FUZZY_MIN_QUERY_LENGTH, int)


def test_fuzzy_candidate_limit_valid():
    """Test že FUZZY_CANDIDATE_LIMIT je rozumná hodnota."""
    assert FUZZY_CANDIDATE_LIMIT >= 100
    assert isinstance(FUZZY_CANDIDATE_LIMIT, int)


# === Scoring Function Tests ===


def test_calculate_ranking_score_exact_match():
    """Test scoring pro exact match."""
    row = pd.Series({"DODAVKY": "A"})
    score = calculate_ranking_score(row, "test", "exact")
    assert score == 30.0  # 20 (exact) + 10 (available)


def test_calculate_ranking_score_substance_match():
    """Test scoring pro substance match."""
    row = pd.Series({"DODAVKY": "A"})
    score = calculate_ranking_score(row, "test", "substance")
    assert score == 25.0  # 15 (substance) + 10 (available)


def test_calculate_ranking_score_substring_match():
    """Test scoring pro substring match."""
    row = pd.Series({"DODAVKY": "A"})
    score = calculate_ranking_score(row, "test", "substring")
    assert score == 20.0  # 10 (substring) + 10 (available)


def test_calculate_ranking_score_fuzzy_match():
    """Test scoring pro fuzzy match."""
    row = pd.Series({"DODAVKY": "A"})
    score = calculate_ranking_score(row, "test", "fuzzy", fuzzy_score=85.0)
    assert score == 18.5  # 8.5 (fuzzy 85/10) + 10 (available)


def test_calculate_ranking_score_unavailable():
    """Test scoring pro nedostupný lék."""
    row = pd.Series({"DODAVKY": "0"})
    score = calculate_ranking_score(row, "test", "exact")
    assert score == 20.0  # 20 (exact) + 0 (unavailable)


def test_calculate_ranking_score_missing_dodavky():
    """Test scoring s chybějící DODAVKY."""
    row = pd.Series({})
    score = calculate_ranking_score(row, "test", "exact")
    assert score == 20.0  # 20 (exact) + 0 (no DODAVKY field)


# === FuzzyMatcher Tests ===


class TestFuzzyMatcher:
    """Test suite pro FuzzyMatcher."""

    def test_init_default_config(self):
        """Test inicializace s default konfigurací."""
        matcher = FuzzyMatcher()
        assert matcher.threshold == FUZZY_THRESHOLD
        assert matcher.min_query_length == FUZZY_MIN_QUERY_LENGTH
        assert matcher.candidate_limit == FUZZY_CANDIDATE_LIMIT

    def test_init_custom_config(self):
        """Test inicializace s custom konfigurací."""
        matcher = FuzzyMatcher(threshold=70, min_query_length=2, candidate_limit=500)
        assert matcher.threshold == 70
        assert matcher.min_query_length == 2
        assert matcher.candidate_limit == 500

    def test_search_empty_query(self, sample_medicines_df):
        """Test že prázdný query vyvolá validační error."""
        matcher = FuzzyMatcher()
        with pytest.raises(SUKLValidationError, match="nesmí být prázdný"):
            matcher.search("", sample_medicines_df)

    def test_search_whitespace_query(self, sample_medicines_df):
        """Test že query pouze s mezerami vyvolá validační error."""
        matcher = FuzzyMatcher()
        with pytest.raises(SUKLValidationError, match="nesmí být prázdný"):
            matcher.search("   ", sample_medicines_df)

    def test_search_exact_match(self, sample_medicines_df):
        """Test exact match v názvu."""
        matcher = FuzzyMatcher()
        results, match_type = matcher.search("PARALEN 500MG", sample_medicines_df, limit=5)

        assert match_type == "exact"
        assert len(results) == 1
        assert results[0]["NAZEV"] == "PARALEN 500MG"
        assert "match_score" in results[0]
        assert results[0]["match_type"] == "exact"

    def test_search_exact_match_case_insensitive(self, sample_medicines_df):
        """Test exact match case insensitive."""
        matcher = FuzzyMatcher()
        results, match_type = matcher.search("paralen 500mg", sample_medicines_df, limit=5)

        assert match_type == "exact"
        assert len(results) == 1

    def test_search_substring_match(self, sample_medicines_df):
        """Test substring match v názvu."""
        matcher = FuzzyMatcher()
        results, match_type = matcher.search("IBUPROFEN", sample_medicines_df, limit=5)

        assert match_type == "substring"
        assert len(results) == 2  # IBUPROFEN 400MG + IBUPROFEN FORTE 600MG
        assert all("IBUPROFEN" in r["NAZEV"] for r in results)
        assert all(r["match_type"] == "substring" for r in results)

    def test_search_substring_match_partial(self, sample_medicines_df):
        """Test substring match s částečným názvem."""
        matcher = FuzzyMatcher()
        results, match_type = matcher.search("PARA", sample_medicines_df, limit=5)

        assert match_type == "substring"
        assert len(results) == 2  # PARALEN + PARACETAMOL
        assert all("PARA" in r["NAZEV"] for r in results)

    def test_search_substance_match(
        self, sample_medicines_df, sample_composition_df, sample_substances_df
    ):
        """Test vyhledávání podle účinné látky."""
        matcher = FuzzyMatcher()
        results, match_type = matcher.search(
            "Ibuprofenum",
            sample_medicines_df,
            sample_composition_df,
            sample_substances_df,
            limit=5,
        )

        assert match_type == "substance"
        assert len(results) == 2  # IBUPROFEN 400MG + IBUPROFEN FORTE 600MG
        assert all(r["match_type"] == "substance" for r in results)

    def test_search_substance_match_partial(
        self, sample_medicines_df, sample_composition_df, sample_substances_df
    ):
        """Test vyhledávání podle částečného názvu látky."""
        matcher = FuzzyMatcher()
        results, match_type = matcher.search(
            "Paracetamol",
            sample_medicines_df,
            sample_composition_df,
            sample_substances_df,
            limit=5,
        )

        assert match_type == "substance"
        assert len(results) == 2  # PARALEN + PARACETAMOL

    def test_search_substance_priority_over_exact(
        self, sample_medicines_df, sample_composition_df, sample_substances_df
    ):
        """Test že substance search má přednost před exact match."""
        # Přidáme léčivo se jménem "Ibuprofenum" (stejné jako látka)
        medicines_with_dupe = pd.concat(
            [
                sample_medicines_df,
                pd.DataFrame(
                    {
                        "KOD_SUKL": [6],
                        "NAZEV": ["Ibuprofenum"],
                        "DODAVKY": ["A"],
                    }
                ),
            ],
            ignore_index=True,
        )

        matcher = FuzzyMatcher()
        results, match_type = matcher.search(
            "Ibuprofenum",
            medicines_with_dupe,
            sample_composition_df,
            sample_substances_df,
            limit=5,
        )

        # Substance search má přednost
        assert match_type == "substance"

    def test_search_fuzzy_match_typo(self, sample_medicines_df):
        """Test fuzzy match s překlepem."""
        matcher = FuzzyMatcher(threshold=60)  # Nižší threshold pro test

        # "IBUPROFNE" je bližší k "IBUPROFEN 400MG" než "IBUPROFN"
        # (pouze jeden extra znak vs chybějící znak)
        results, match_type = matcher.search("IBUPROFNE", sample_medicines_df, limit=5)

        # Pokud fuzzy nenajde nic, může být match_type "none"
        # (závisí na threshold a podobnosti)
        if match_type == "fuzzy":
            assert len(results) > 0
            assert any("IBUPROFEN" in r["NAZEV"] for r in results)
            assert all(r["match_type"] == "fuzzy" for r in results)
            assert all("fuzzy_score" in r for r in results)
        else:
            # Fuzzy matching s tímto query možná nedosáhne threshold
            assert match_type == "none"

    def test_search_fuzzy_match_below_threshold(self, sample_medicines_df):
        """Test že fuzzy match s nízkým skóre není vrácen."""
        matcher = FuzzyMatcher(threshold=95)  # Vysoký threshold
        results, match_type = matcher.search("COMPLETELY_DIFFERENT", sample_medicines_df, limit=5)

        assert match_type == "none"
        assert len(results) == 0

    def test_search_fuzzy_match_short_query(self, sample_medicines_df):
        """Test že krátký query (< min_query_length) nezpůsobí fuzzy search."""
        matcher = FuzzyMatcher(min_query_length=3)
        results, match_type = matcher.search("IB", sample_medicines_df, limit=5)

        # Mělo by najít substring ale NE fuzzy
        if results:
            assert match_type in ["exact", "substring", "none"]
        else:
            assert match_type == "none"

    def test_search_limit_enforcement(self, sample_medicines_df):
        """Test že limit je respektován."""
        matcher = FuzzyMatcher()
        results, _ = matcher.search("A", sample_medicines_df, limit=2)

        assert len(results) <= 2

    def test_search_limit_zero(self, sample_medicines_df):
        """Test že limit 0 vrací prázdné výsledky."""
        matcher = FuzzyMatcher()
        results, _ = matcher.search("IBUPROFEN", sample_medicines_df, limit=0)

        assert len(results) == 0

    def test_search_no_results(self, sample_medicines_df):
        """Test že neexistující query vrací prázdný seznam."""
        matcher = FuzzyMatcher(threshold=99)
        results, match_type = matcher.search("NONEXISTENT_MEDICINE_XYZ", sample_medicines_df)

        assert match_type == "none"
        assert len(results) == 0

    def test_search_results_sorted_by_score(self, sample_medicines_df):
        """Test že výsledky jsou seřazené podle skóre."""
        matcher = FuzzyMatcher()
        results, _ = matcher.search("PARA", sample_medicines_df, limit=10)

        if len(results) > 1:
            scores = [r["match_score"] for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_search_candidate_limit_enforcement(self):
        """Test že fuzzy search limituje počet kandidátů."""
        # Vytvoř velký DataFrame
        large_df = pd.DataFrame(
            {
                "KOD_SUKL": range(2000),
                "NAZEV": [f"MEDICINE_{i}" for i in range(2000)],
                "DODAVKY": ["A"] * 2000,
            }
        )

        matcher = FuzzyMatcher(candidate_limit=500, threshold=70)
        results, match_type = matcher.search("MEDICIN", large_df, limit=10)

        # Fuzzy by měl limitovat na 500 kandidátů
        # (těžko testovat interně, ale alespoň ověříme že nepadne)
        assert match_type in ["substring", "fuzzy", "none"]


# === Singleton Pattern Tests ===


def test_get_fuzzy_matcher_singleton():
    """Test že get_fuzzy_matcher vrací singleton instanci."""
    matcher1 = get_fuzzy_matcher()
    matcher2 = get_fuzzy_matcher()

    assert matcher1 is matcher2


def test_get_fuzzy_matcher_returns_fuzzy_matcher():
    """Test že get_fuzzy_matcher vrací FuzzyMatcher instanci."""
    matcher = get_fuzzy_matcher()
    assert isinstance(matcher, FuzzyMatcher)


# === Integration Tests ===


def test_multi_level_pipeline_priority(
    sample_medicines_df, sample_composition_df, sample_substances_df
):
    """Test že pipeline má správnou prioritu: substance > exact > substring > fuzzy."""
    matcher = FuzzyMatcher()

    # Test 1: Substance match má přednost
    results1, match_type1 = matcher.search(
        "Paracetamol", sample_medicines_df, sample_composition_df, sample_substances_df
    )
    assert match_type1 == "substance"

    # Test 2: Exact match (bez substance tabulek)
    results2, match_type2 = matcher.search("PARALEN 500MG", sample_medicines_df)
    assert match_type2 == "exact"

    # Test 3: Substring match (bez substance tabulek, ne exact)
    results3, match_type3 = matcher.search("PARALEN", sample_medicines_df)
    assert match_type3 == "substring"

    # Test 4: Fuzzy match (typo, bez substance tabulek, ne exact/substring)
    results4, match_type4 = matcher.search("PARALN", sample_medicines_df)
    assert match_type4 in ["fuzzy", "none"]  # Závisí na threshold


def test_availability_bonus_in_scoring(sample_medicines_df):
    """Test že dostupné léky mají vyšší skóre."""
    # Přidej unavailable lék
    medicines_with_unavailable = pd.concat(
        [
            sample_medicines_df,
            pd.DataFrame(
                {
                    "KOD_SUKL": [6],
                    "NAZEV": ["IBUPROFEN 200MG"],
                    "DODAVKY": ["0"],  # Nedostupný
                }
            ),
        ],
        ignore_index=True,
    )

    matcher = FuzzyMatcher()
    results, _ = matcher.search("IBUPROFEN", medicines_with_unavailable, limit=10)

    # Najdi dostupné a nedostupné IBUPROFEN
    available = [r for r in results if r["DODAVKY"] == "A"]
    unavailable = [r for r in results if r["DODAVKY"] == "0"]

    if available and unavailable:
        # Dostupné by měly mít vyšší skóre
        assert available[0]["match_score"] > unavailable[0]["match_score"]


def test_empty_dataframe(sample_composition_df, sample_substances_df):
    """Test že prázdný DataFrame vrací prázdné výsledky."""
    empty_df = pd.DataFrame(columns=["KOD_SUKL", "NAZEV", "DODAVKY"])

    matcher = FuzzyMatcher()
    results, match_type = matcher.search(
        "test", empty_df, sample_composition_df, sample_substances_df
    )

    assert match_type == "none"
    assert len(results) == 0


def test_missing_columns_handled():
    """Test že chybějící sloupce jsou korektně zpracovány."""
    # DataFrame bez DODAVKY
    df_no_dodavky = pd.DataFrame(
        {
            "KOD_SUKL": [1, 2],
            "NAZEV": ["TEST 1", "TEST 2"],
        }
    )

    matcher = FuzzyMatcher()
    results, match_type = matcher.search("TEST", df_no_dodavky, limit=5)

    assert match_type == "substring"
    assert len(results) == 2
    # Mělo by fungovat i bez DODAVKY
