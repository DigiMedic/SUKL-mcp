"""
Smart search s fuzzy matchingem pro SÚKL léčivé přípravky.

Implementuje multi-level search pipeline:
1. Vyhledávání v účinné látce
2. Exact/substring match v názvu
3. Fuzzy fallback (shoda > threshold)
"""

import logging
from typing import Any, Optional

import pandas as pd
from rapidfuzz import fuzz, process

from sukl_mcp.exceptions import SUKLValidationError

logger = logging.getLogger(__name__)

# === Configuration ===

FUZZY_THRESHOLD = 80  # Minimální skóre pro fuzzy match (0-100)
FUZZY_MIN_QUERY_LENGTH = 3  # Minimální délka query pro fuzzy search
FUZZY_CANDIDATE_LIMIT = 1000  # Max kandidátů pro fuzzy matching


# === Scoring Functions ===


def calculate_ranking_score(
    row: pd.Series,
    query: str,
    match_type: str,
    fuzzy_score: float = 0.0,
) -> float:
    """
    Vypočítej celkové skóre pro ranking výsledků.

    Args:
        row: Pandas Series s daty léčiva
        query: Původní vyhledávací dotaz
        match_type: Typ matchování ("substance", "exact", "substring", "fuzzy")
        fuzzy_score: Skóre z fuzzy matchingu (0-100)

    Returns:
        Celkové skóre (vyšší = relevantnější)
    """
    score = 0.0

    # Match type scoring
    if match_type == "exact":
        score += 20.0
    elif match_type == "substance":
        score += 15.0
    elif match_type == "substring":
        score += 10.0
    elif match_type == "fuzzy":
        score += fuzzy_score / 10.0  # 0-10 bodů

    # Dostupnost bonus
    if pd.notna(row.get("DODAVKY")) and str(row.get("DODAVKY")).upper() == "A":
        score += 10.0

    # Úhrada bonus (pokud existuje sloupec)
    # TODO: Přidat po implementaci EPIC 3
    # if row.get("has_reimbursement"):
    #     score += 5.0

    return score


# === Multi-Level Search Pipeline ===


class FuzzyMatcher:
    """
    Smart vyhledávač s multi-level pipeline a fuzzy fallbackem.

    Pipeline:
    1. Vyhledávání v účinné látce (dlp_slozeni)
    2. Exact match v názvu
    3. Substring match v názvu
    4. Fuzzy fallback (rapidfuzz)
    """

    def __init__(
        self,
        threshold: int = FUZZY_THRESHOLD,
        min_query_length: int = FUZZY_MIN_QUERY_LENGTH,
        candidate_limit: int = FUZZY_CANDIDATE_LIMIT,
    ):
        """
        Args:
            threshold: Minimální skóre pro fuzzy match (0-100)
            min_query_length: Minimální délka query pro fuzzy
            candidate_limit: Max kandidátů pro fuzzy matching
        """
        self.threshold = threshold
        self.min_query_length = min_query_length
        self.candidate_limit = candidate_limit

    def search(
        self,
        query: str,
        df_medicines: pd.DataFrame,
        df_composition: Optional[pd.DataFrame] = None,
        df_substances: Optional[pd.DataFrame] = None,
        limit: int = 20,
    ) -> tuple[list[dict], str]:
        """
        Proveď multi-level search.

        Args:
            query: Vyhledávací dotaz
            df_medicines: DataFrame s léčivými přípravky
            df_composition: Optional DataFrame se složením
            df_substances: Optional DataFrame s účinnými látkami
            limit: Max počet výsledků

        Returns:
            Tuple (results, match_type) kde match_type je "substance", "exact", "substring", nebo "fuzzy"

        Raises:
            SUKLValidationError: Při neplatném vstupu
        """
        # Input validace
        if not query or not query.strip():
            raise SUKLValidationError("Query nesmí být prázdný")

        query = query.strip()
        query_lower = query.lower()

        # Step 1: Vyhledávání v účinné látce
        if df_composition is not None and df_substances is not None:
            results = self._search_by_substance(
                query_lower, df_medicines, df_composition, df_substances, limit
            )
            if results:
                logger.info(f"Found {len(results)} results via substance search")
                return (results, "substance")

        # Step 2: Exact match v názvu
        results = self._search_exact(query_lower, df_medicines, limit)
        if results:
            logger.info(f"Found {len(results)} results via exact match")
            return (results, "exact")

        # Step 3: Substring match v názvu
        results = self._search_substring(query_lower, df_medicines, limit)
        if results:
            logger.info(f"Found {len(results)} results via substring match")
            return (results, "substring")

        # Step 4: Fuzzy fallback
        if len(query) >= self.min_query_length:
            results = self._search_fuzzy(query_lower, df_medicines, limit)
            if results:
                logger.info(f"Found {len(results)} results via fuzzy match")
                return (results, "fuzzy")

        logger.info("No results found for query")
        return ([], "none")

    def _search_by_substance(
        self,
        query: str,
        df_medicines: pd.DataFrame,
        df_composition: pd.DataFrame,
        df_substances: pd.DataFrame,
        limit: int,
    ) -> list[dict]:
        """Vyhledej podle účinné látky."""
        # Najdi účinné látky obsahující query
        mask = df_substances["NAZEV"].str.contains(query, case=False, na=False, regex=False)
        matching_substances = df_substances[mask]

        if matching_substances.empty:
            return []

        # Získej KOD_LATKY pro matching látky
        substance_codes = matching_substances["KOD"].unique()

        # Najdi složení obsahující tyto látky
        composition_mask = df_composition["KOD_LATKY"].isin(substance_codes)
        matching_compositions = df_composition[composition_mask]

        if matching_compositions.empty:
            return []

        # Získej KOD_SUKL léčiv
        medicine_codes = matching_compositions["KOD_SUKL"].unique()

        # Filtruj léčiva
        medicine_mask = df_medicines["KOD_SUKL"].isin(medicine_codes)
        results_df = df_medicines[medicine_mask]

        # Add scoring
        results_df = results_df.copy()
        results_df["_score"] = results_df.apply(
            lambda row: calculate_ranking_score(row, query, "substance"),
            axis=1,
        )

        # Sort by score
        results_df = results_df.sort_values("_score", ascending=False)

        # Limit a konverze
        results = results_df.head(limit).to_dict("records")

        # Přidej match metadata
        for result in results:
            result["match_score"] = result.pop("_score", 0.0)
            result["match_type"] = "substance"

        return results

    def _search_exact(
        self,
        query: str,
        df_medicines: pd.DataFrame,
        limit: int,
    ) -> list[dict]:
        """Exact match v názvu."""
        mask = df_medicines["NAZEV"].str.lower() == query
        results_df = df_medicines[mask]

        if results_df.empty:
            return []

        # Add scoring
        results_df = results_df.copy()
        results_df["_score"] = results_df.apply(
            lambda row: calculate_ranking_score(row, query, "exact"),
            axis=1,
        )

        # Sort by score
        results_df = results_df.sort_values("_score", ascending=False)

        # Limit a konverze
        results = results_df.head(limit).to_dict("records")

        # Přidej match metadata
        for result in results:
            result["match_score"] = result.pop("_score", 0.0)
            result["match_type"] = "exact"

        return results

    def _search_substring(
        self,
        query: str,
        df_medicines: pd.DataFrame,
        limit: int,
    ) -> list[dict]:
        """Substring match v názvu."""
        mask = df_medicines["NAZEV"].str.contains(query, case=False, na=False, regex=False)
        results_df = df_medicines[mask]

        if results_df.empty:
            return []

        # Add scoring
        results_df = results_df.copy()
        results_df["_score"] = results_df.apply(
            lambda row: calculate_ranking_score(row, query, "substring"),
            axis=1,
        )

        # Sort by score
        results_df = results_df.sort_values("_score", ascending=False)

        # Limit a konverze
        results = results_df.head(limit).to_dict("records")

        # Přidej match metadata
        for result in results:
            result["match_score"] = result.pop("_score", 0.0)
            result["match_type"] = "substring"

        return results

    def _search_fuzzy(
        self,
        query: str,
        df_medicines: pd.DataFrame,
        limit: int,
    ) -> list[dict]:
        """
        Fuzzy match s rapidfuzz.

        Používá WRatio scorer pro nejlepší výsledky.
        """
        # Limit kandidátů pro performance
        candidates_df = df_medicines.head(self.candidate_limit)

        # Extrahuj názvy pro fuzzy matching
        names = candidates_df["NAZEV"].fillna("").tolist()

        # Fuzzy match s rapidfuzz
        matches = process.extract(
            query,
            names,
            scorer=fuzz.WRatio,
            limit=limit * 2,  # Získej více než limit pro filtering
        )

        # Filtruj podle threshold
        filtered_matches = [(name, score, idx) for name, score, idx in matches if score >= self.threshold]

        if not filtered_matches:
            return []

        # Získej indexy matching záznamů
        indices = [idx for _, _, idx in filtered_matches]
        results_df = candidates_df.iloc[indices].copy()

        # Přidej fuzzy score
        fuzzy_scores = {idx: score for _, score, idx in filtered_matches}
        results_df["_fuzzy_score"] = results_df.index.map(fuzzy_scores)

        # Calculate final score
        results_df["_score"] = results_df.apply(
            lambda row: calculate_ranking_score(
                row, query, "fuzzy", fuzzy_score=row["_fuzzy_score"]
            ),
            axis=1,
        )

        # Sort by score
        results_df = results_df.sort_values("_score", ascending=False)

        # Limit a konverze
        results = results_df.head(limit).to_dict("records")

        # Přidej match metadata
        for result in results:
            result["match_score"] = result.pop("_score", 0.0)
            result["fuzzy_score"] = result.pop("_fuzzy_score", 0.0)
            result["match_type"] = "fuzzy"

        return results


# === Singleton Instance ===

_matcher: Optional[FuzzyMatcher] = None


def get_fuzzy_matcher() -> FuzzyMatcher:
    """
    Získej singleton instanci FuzzyMatcher.

    Returns:
        FuzzyMatcher instance
    """
    global _matcher
    if _matcher is None:
        _matcher = FuzzyMatcher()
    return _matcher
