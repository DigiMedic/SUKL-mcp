"""
CSV-based klient pro SÚKL Open Data.

Načítá data z DLP CSV souborů a poskytuje in-memory vyhledávání.
"""

import asyncio
import logging
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

import httpx
import pandas as pd
from pydantic import BaseModel, Field
from rapidfuzz import fuzz

# Absolutní import pro FastMCP Cloud compatibility
from sukl_mcp.exceptions import SUKLValidationError, SUKLZipBombError

# Type checking imports (circular dependency prevention)
if TYPE_CHECKING:
    from sukl_mcp.models import AvailabilityStatus

logger = logging.getLogger(__name__)


def _get_opendata_url() -> str:
    """Get SÚKL Open Data URL from ENV or default."""
    return os.getenv(
        "SUKL_OPENDATA_URL",
        "https://opendata.sukl.cz/soubory/SOD20251223/DLP20251223.zip",
    )


def _get_pharmacy_url() -> str:
    """Get SÚKL pharmacy list URL from ENV or default."""
    return os.getenv(
        "SUKL_PHARMACY_URL",
        "https://opendata.sukl.cz/soubory/SOD20251223/LEKARNY20251223.zip",
    )


def _get_cache_dir() -> Path:
    """Get cache directory from ENV or default.

    Priority order (container-friendly):
    1. Environment variable SUKL_CACHE_DIR
    2. /tmp/sukl_dlp_cache (writeable in containers)
    3. Local cache/ (development)
    """
    # 1. Priority: Environment variable
    env_dir = os.getenv("SUKL_CACHE_DIR")
    if env_dir:
        return Path(env_dir)

    # 2. Priority: /tmp (kontejner-friendly)
    tmp_cache = Path("/tmp/sukl_dlp_cache")
    # Pokud jsme v kontejneru (Path.cwd() není writeable), preferujeme /tmp
    if tmp_cache.exists() or not os.access(os.getcwd(), os.W_OK):
        return tmp_cache

    # 3. Priority: Lokální cache/
    cwd_cache = Path.cwd() / "cache"
    if cwd_cache.exists():
        return cwd_cache

    # Fallback: Vždy /tmp
    return Path("/tmp/sukl_dlp_cache")


def _get_data_dir() -> Path:
    """Get data directory from ENV or default.

    Priority order (container-friendly):
    1. Environment variable SUKL_DATA_DIR
    2. /tmp/sukl_dlp_data (writeable in containers)
    3. Local data/ directory (development only)
    4. Project data/ directory (development only)
    """
    # 1. Priority: Environment variable
    env_dir = os.getenv("SUKL_DATA_DIR")
    if env_dir:
        return Path(env_dir)

    # 2. Priority: /tmp (kontejner-friendly)
    tmp_data = Path("/tmp/sukl_dlp_data")
    # Pokud jsme v kontejneru (Path.cwd() není writeable), preferujeme /tmp
    if tmp_data.exists() or not os.access(os.getcwd(), os.W_OK):
        return tmp_data

    # 3. Priority: Lokální data/ (development)
    cwd_data = Path.cwd() / "data"
    if cwd_data.exists() and (cwd_data / "dlp_lecivepripravky.csv").exists():
        return cwd_data

    # 4. Priority: Project data/ (development)
    base_dir = Path(__file__).parent.parent.parent
    default_dir = base_dir / "data"
    if default_dir.exists() and (default_dir / "dlp_lecivepripravky.csv").exists():
        return default_dir

    # Fallback: Vždy /tmp pro kontejnery
    return Path("/tmp/sukl_dlp_data")


def _get_download_timeout() -> float:
    """Get download timeout from ENV or default."""
    return float(os.getenv("SUKL_DOWNLOAD_TIMEOUT", "120.0"))


class SUKLConfig(BaseModel):
    """Konfigurace SÚKL klienta (konfigurovatelné přes ENV)."""

    # Open Data URL
    opendata_dlp_url: str = Field(default_factory=_get_opendata_url)
    opendata_pharmacy_url: str = Field(default_factory=_get_pharmacy_url)

    # Local cache
    cache_dir: Path = Field(default_factory=_get_cache_dir)
    data_dir: Path = Field(default_factory=_get_data_dir)

    # Download timeout
    download_timeout: float = Field(default_factory=_get_download_timeout)


class SUKLDataFetcher:
    """Loader pro SÚKL CSV data."""

    def __init__(self, config: SUKLConfig | None = None):
        self.config = config or SUKLConfig()
        self._data: dict[str, pd.DataFrame] = {}
        self._loaded = False

    async def load_data(self) -> None:
        """Stáhni a načti DLP data."""
        if self._loaded:
            logger.info("Data již načtena")
            return

        logger.info("Načítám SÚKL DLP data...")

        for d in [self.config.cache_dir, self.config.data_dir]:
            if not d.exists():
                try:
                    d.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    logger.warning(f"Nepodařilo se vytvořit adresář {d}: {e}")

        # Stáhni a rozbal DLP ZIP
        dlp_zip_path = self.config.cache_dir / "DLP.zip"
        if not dlp_zip_path.exists():
            await self._download_zip(dlp_zip_path, self.config.opendata_dlp_url)

        if not (self.config.data_dir / "dlp_lecivepripravky.csv").exists():
            await self._extract_zip(dlp_zip_path)

        # Stáhni a rozbal seznam lékáren
        lekarny_zip_path = self.config.cache_dir / "LEKARNY.zip"
        if not lekarny_zip_path.exists():
            await self._download_zip(lekarny_zip_path, self.config.opendata_pharmacy_url)

        if not (self.config.data_dir / "lekarny_seznam.csv").exists():
            await self._extract_zip(lekarny_zip_path)

        # Načti klíčové CSV soubory
        await self._load_csvs()

        self._loaded = True
        logger.info(f"Data načtena: {len(self._data)} tabulek")

    async def _download_zip(self, zip_path: Path, url: str) -> None:
        """Stáhni ZIP soubor z URL."""
        logger.info(f"Stahuji {url}...")

        async with httpx.AsyncClient(timeout=self.config.download_timeout) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()

                with open(zip_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

        logger.info(f"Staženo: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")

    async def _extract_zip(self, zip_path: Path) -> None:
        """Rozbal ZIP soubor (async přes executor + ZIP bomb protection)."""
        logger.info(f"Rozbaluji {zip_path}...")

        def _sync_extract() -> None:
            """Synchronní extrakce s bezpečnostní kontrolou."""
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # ZIP bomb protection - kontrola celkové velikosti
                total_size = sum(info.file_size for info in zip_ref.infolist())
                max_size = 5 * 1024 * 1024 * 1024  # 5 GB
                if total_size > max_size:
                    raise SUKLZipBombError(
                        f"ZIP příliš velký: {total_size / 1024 / 1024:.1f} MB "
                        f"(maximum: {max_size / 1024 / 1024:.1f} MB)"
                    )

                zip_ref.extractall(self.config.data_dir)

        # Spusť v executoru aby neblokovala event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _sync_extract)

        logger.info(f"Rozbaleno do {self.config.data_dir}")

    async def _load_csvs(self) -> None:
        """Načti CSV soubory paralelně do pandas DataFrames."""
        logger.info("Načítám CSV soubory...")

        # Klíčové tabulky DLP
        tables = [
            "dlp_lecivepripravky",  # Hlavní tabulka léčiv
            "dlp_slozeni",  # Složení
            "dlp_lecivelatky",  # Léčivé látky
            "dlp_atc",  # ATC kódy
            "dlp_nazvydokumentu",  # Dokumenty (PIL)
            # "dlp_cau",  # TODO: Pricing data není v SÚKL Open Data ZIP
            # Tabulky lékáren
            "lekarny_seznam",  # Seznam lékáren
            "lekarny_prac_doba",  # Pracovní doba
            "lekarny_typ",  # Typy lékáren
        ]

        def _load_single_csv(table: str) -> tuple[str, pd.DataFrame | None]:
            """Načti jeden CSV soubor (synchronní funkce pro executor)."""
            csv_path = self.config.data_dir / f"{table}.csv"
            if not csv_path.exists():
                return (table, None)

            df = pd.read_csv(
                csv_path,
                sep=";",
                encoding="cp1250",
                low_memory=False,
                dtype_backend="pyarrow",
            )
            return (table, df)

        # Paralelní načítání všech CSV souborů
        loop = asyncio.get_event_loop()
        results = await asyncio.gather(
            *[loop.run_in_executor(None, _load_single_csv, t) for t in tables]
        )

        # Uložení načtených dat a logování
        for table, df in results:
            if df is not None:
                self._data[table] = df
                logger.info(f"  ✓ {table}: {len(df)} záznamů")
            else:
                logger.warning(f"  ✗ {table}: soubor nenalezen")

    def get_table(self, name: str) -> pd.DataFrame | None:
        """Získej DataFrame tabulky."""
        return self._data.get(name)


class SUKLClient:
    """Async klient pro SÚKL CSV data."""

    def __init__(self, config: SUKLConfig | None = None):
        self.config = config or SUKLConfig()
        self._loader = SUKLDataFetcher(config)
        self._initialized = False

    async def initialize(self) -> None:
        """Inicializuj klienta a načti data."""
        if self._initialized:
            return

        logger.info("Inicializuji SÚKL klienta...")
        await self._loader.load_data()
        self._initialized = True

    async def health_check(self) -> dict[str, Any]:
        """Health check."""
        return {
            "status": "ok" if self._initialized else "not_initialized",
            "tables_loaded": len(self._loader._data),
            "timestamp": datetime.now().isoformat(),
        }

    async def get_document_filename(
        self,
        sukl_code: str,
        doc_type: Literal["pil", "spc"],
    ) -> str | None:
        """
        Získej filename dokumentu (PIL nebo SPC) z CSV dlp_nazvydokumentu.csv.

        Args:
            sukl_code: SÚKL kód léčiva
            doc_type: Typ dokumentu ("pil" nebo "spc")

        Returns:
            Filename (např. PI223082.pdf) nebo None
        """
        df_docs = self._loader.get_table("dlp_nazvydokumentu")
        if df_docs is None or df_docs.empty:
            return None

        sukl_int = int(sukl_code) if sukl_code.isdigit() else None
        if sukl_int is None:
            return None

        # Filtruj podle SÚKL kódu
        row = df_docs[df_docs["KOD_SUKL"] == sukl_int]

        if row.empty:
            return None

        column = doc_type.upper()  # "PIL" nebo "SPC"
        filename = row.iloc[0][column]

        if pd.isna(filename) or not filename:
            return None

        return filename

    async def search_medicines(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        only_available: bool = False,
        only_reimbursed: bool = False,
        use_fuzzy: bool = True,
    ) -> tuple[list[dict], str]:
        """
        Vyhledej léčivé přípravky s multi-level pipeline a fuzzy fallbackem.

        Args:
            query: Vyhledávací dotaz
            limit: Max počet výsledků
            offset: Offset pro paging
            only_available: Filtr pouze dostupné léky
            only_reimbursed: Filtr pouze hrazené léky
            use_fuzzy: Použít fuzzy matching (default: True)

        Returns:
            Tuple (results, match_type) kde match_type je "substance", "exact", "substring", "fuzzy", nebo "none"

        Raises:
            SUKLValidationError: Při neplatném vstupu
        """
        # Import zde aby se předešlo circular dependencies
        from sukl_mcp.fuzzy_search import get_fuzzy_matcher

        # Input validace
        if not query or not query.strip():
            raise SUKLValidationError("Query nesmí být prázdný")
        if len(query) > 200:
            raise SUKLValidationError(f"Query příliš dlouhý: {len(query)} znaků (maximum: 200)")
        if not (1 <= limit <= 100):
            raise SUKLValidationError(f"Limit musí být 1-100 (zadáno: {limit})")

        query = query.strip()

        if not self._initialized:
            await self.initialize()

        df_medicines = self._loader.get_table("dlp_lecivepripravky")
        if df_medicines is None:
            return ([], "none")

        # Aplikuj pre-filtry
        if only_available:
            df_medicines = df_medicines[df_medicines["DODAVKY"].str.upper() == "A"].copy()

        if only_reimbursed:
            # NOTE: Reimbursement filtering je implementováno post-enrichment
            # protože cenová data jsou v separátní tabulce (dlp_cau).
            # Pre-filtering by vyžadoval DataFrame merge což je nákladné.
            # Pro filtrování podle úhrad použij price data z výsledků.
            pass

        if df_medicines.empty:
            return ([], "none")

        # Multi-level search s fuzzy fallbackem
        if use_fuzzy:
            matcher = get_fuzzy_matcher()

            # Získej optional tabulky pro substance search
            df_composition = self._loader.get_table("dlp_slozeni")
            df_substances = self._loader.get_table("dlp_lecivelatky")

            results, match_type = await matcher.search(
                query=query,
                df_medicines=df_medicines,
                df_composition=df_composition,
                df_substances=df_substances,
                limit=limit + offset,  # Fetch více pro offset
            )

            # Aplikuj offset
            if offset > 0:
                results = results[offset:]

        else:
            # Legacy simple substring search (zpětná kompatibilita)
            mask = df_medicines["NAZEV"].str.contains(query, case=False, na=False, regex=False)
            results_df = df_medicines[mask]

            # Paging
            results_df = results_df.iloc[offset : offset + limit]

            # Konverze na dict
            results = results_df.to_dict("records")

            # Přidej match metadata pro konzistenci
            for result in results:
                result["match_score"] = 10.0  # Default score
                result["match_type"] = "substring"

            match_type = "substring" if results else "none"

        # Obohacení výsledků o cenové údaje (EPIC 3)
        results = await self._enrich_with_price_data(results)

        return (results, match_type)

    def _normalize_availability(self, value: Any) -> "AvailabilityStatus":
        """
        Normalizuj hodnotu DODAVKY na AvailabilityStatus enum.

        Podporuje různé formáty hodnot z CSV:
        - "1", "A", "ANO" → AVAILABLE
        - "0", "N", "NE" → UNAVAILABLE
        - None, NaN, jiné → UNKNOWN

        Args:
            value: Hodnota z sloupce DODAVKY

        Returns:
            AvailabilityStatus enum hodnota
        """
        # Import zde pro circular dependency
        from sukl_mcp.models import AvailabilityStatus

        if pd.isna(value):
            return AvailabilityStatus.UNKNOWN

        # Pokud je to float, převeď na int (1.0 → 1, 0.0 → 0)
        if isinstance(value, float):
            if value == int(value):  # Celé číslo jako float
                value = int(value)

        # Konverze na string a normalizace
        str_val = str(value).strip().upper()

        # Dostupné varianty
        if str_val in ("1", "A", "ANO", "YES", "AVAILABLE", "TRUE"):
            return AvailabilityStatus.AVAILABLE

        # Nedostupné varianty
        if str_val in ("0", "N", "NE", "NO", "UNAVAILABLE", "FALSE"):
            return AvailabilityStatus.UNAVAILABLE

        # Neznámé/neplatné hodnoty
        return AvailabilityStatus.UNKNOWN

    def _parse_strength(self, strength_str: str) -> tuple[float | None, str]:
        """
        Parsuj sílu přípravku na numerickou hodnotu a jednotku.

        Podporované formáty:
        - "500mg", "500 mg", "500MG"
        - "2.5g", "2,5 g", "2.5 G"
        - "100ml", "10%" (procenta)
        - "1000iu", "1000 IU" (international units)
        - Kombinace: "500mg/5ml"

        Args:
            strength_str: String reprezentující sílu (např. "500mg")

        Returns:
            tuple[Optional[float], str]: (numerická hodnota, jednotka)
            Pokud parsing selže, vrací (None, original_string)
        """
        # Kontrola NA musí být PRVNÍ (před boolean evaluací)
        if pd.isna(strength_str):
            return (None, "")

        if not strength_str:
            return (None, "")

        strength_str = str(strength_str).strip()

        if not strength_str:
            return (None, "")

        # Regex patterns pro parsování
        # Pattern 1: Číslo + jednotka (500mg, 2.5g, 100ml, 10%, 1000iu)
        pattern = r"(\d+[.,]?\d*)\s*([a-zA-Z%]+)"

        match = re.search(pattern, strength_str, re.IGNORECASE)

        if match:
            # Extrahuj numerickou hodnotu
            num_str = match.group(1)
            # Normalizuj českou desetinnou čárku na tečku
            num_str = num_str.replace(",", ".")

            try:
                value = float(num_str)
            except ValueError:
                return (None, strength_str)

            # Extrahuj a normalizuj jednotku
            unit = match.group(2).upper()

            # Normalizace jednotek
            # G → MG (gram na miligram, převod 1g = 1000mg)
            if unit == "G":
                value = value * 1000  # Převod na mg
                unit = "MG"

            return (value, unit)

        # Pokud regex nesedí, zkus najít alespoň číslo
        num_pattern = r"(\d+[.,]?\d*)"
        num_match = re.search(num_pattern, strength_str)

        if num_match:
            num_str = num_match.group(1).replace(",", ".")
            try:
                value = float(num_str)
                return (value, "")  # Číslo bez jednotky
            except ValueError:
                pass

        # Parsing selhal, vrať None a původní string
        return (None, strength_str)

    def _calculate_strength_similarity(self, str1: str, str2: str) -> float:
        """
        Vypočítej podobnost dvou sil přípravku.

        Vrací hodnotu 0.0 - 1.0, kde:
        - 1.0 = identická síla
        - 0.5-0.9 = podobná síla (stejná jednotka, jiná hodnota)
        - 0.3 = různé jednotky
        - 0.0 = nelze porovnat

        Args:
            str1: První síla (např. "500mg")
            str2: Druhá síla (např. "1000mg")

        Returns:
            float: Podobnost (0.0 - 1.0)
        """
        # Parse obě hodnoty
        val1, unit1 = self._parse_strength(str1)
        val2, unit2 = self._parse_strength(str2)

        # Pokud parsing selhal, fallback na string comparison
        if val1 is None or val2 is None:
            # Pokud jsou stringy identické, vrať 0.5
            if str1 and str2 and str1.lower().strip() == str2.lower().strip():
                return 0.5
            # Jinak nelze porovnat
            return 0.0

        # Pokud jednotky neodpovídají
        if unit1 != unit2:
            return 0.3  # Nízká podobnost (různé jednotky)

        # Pokud jsou jednotky stejné, porovnej numerické hodnoty
        # Vypočítej ratio (menší/větší), aby výsledek byl 0.0-1.0
        if val1 == val2:
            return 1.0  # Identické

        ratio = min(val1, val2) / max(val1, val2)

        # ratio je v rozsahu 0.0-1.0
        # Např: 500mg vs 1000mg → ratio = 0.5
        # Např: 900mg vs 1000mg → ratio = 0.9
        return ratio

    def _rank_alternatives(self, candidates: list[dict], original: dict) -> list[dict]:
        """
        Rankuj alternativní léčiva podle relevance k originálnímu přípravku.

        Multi-kriteriální ranking:
        - Forma (40 bodů): Shoda lékové formy (tableta, sirup, atd.)
        - Síla (30 bodů): Podobnost dávkování
        - Cena (20 bodů): Cenová dostupnost (nižší cena = vyšší skóre)
        - Název (10 bodů): Fuzzy shoda názvů

        Args:
            candidates: Seznam kandidátních alternativ (dict records)
            original: Originální léčivo (dict record)

        Returns:
            list[dict]: Seřazený seznam (nejvyšší skóre první) s přidaným
                        polem 'relevance_score' (0-100)
        """
        # Extrahuj vlastnosti originálního léčiva
        original_form = original.get("FORMA", "").lower().strip()
        original_strength = original.get("SILA", "")
        original_name = original.get("NAZEV", "")
        original_price = original.get("max_price")

        # Rankuj každého kandidáta
        for candidate in candidates:
            score = 0.0

            # 1. Forma match (40 bodů)
            candidate_form = candidate.get("FORMA", "").lower().strip()
            if candidate_form and original_form:
                if candidate_form == original_form:
                    score += 40.0
                else:
                    # Částečná shoda (např. "tableta" vs "tableta obalená")
                    if candidate_form in original_form or original_form in candidate_form:
                        score += 20.0

            # 2. Síla similarity (30 bodů)
            candidate_strength = candidate.get("SILA", "")
            if candidate_strength and original_strength:
                strength_sim = self._calculate_strength_similarity(
                    original_strength, candidate_strength
                )
                score += strength_sim * 30.0

            # 3. Cena (20 bodů) - nižší cena = vyšší skóre
            candidate_price = candidate.get("max_price")
            if candidate_price is not None and original_price is not None:
                # Normalizuj cenový rozdíl
                # Pokud kandidát je levnější nebo stejně drahý, plný počet bodů
                # Pokud kandidát je dražší, snížené body
                if candidate_price <= original_price:
                    score += 20.0
                else:
                    # Vypočítej ratio (menší/větší)
                    price_ratio = original_price / candidate_price
                    score += price_ratio * 20.0

            # 4. Název similarity (10 bodů)
            candidate_name = candidate.get("NAZEV", "")
            if candidate_name and original_name:
                # Fuzzy matching na název
                name_sim = fuzz.ratio(original_name, candidate_name) / 100.0
                score += name_sim * 10.0

            # Uložení skóre do kandidáta
            candidate["relevance_score"] = round(score, 2)

        # Seřaď kandidáty podle skóre (nejvyšší první)
        ranked = sorted(candidates, key=lambda x: x.get("relevance_score", 0.0), reverse=True)

        return ranked

    async def find_generic_alternatives(self, sukl_code: str, limit: int = 10) -> list[dict]:
        """
        Najdi generické alternativy pro nedostupný lék.

        Implementuje kombinovanou strategii:
        1. Primary: Hledání léků se stejnou účinnou látkou
        2. Fallback: Hledání léků ve stejné ATC skupině (3-char prefix)

        Args:
            sukl_code: SÚKL kód nedostupného léčiva
            limit: Max počet alternativ (default: 10)

        Returns:
            list[dict]: Seřazený seznam alternativ obohacený o cenové údaje
                        Prázdný list pokud lék je dostupný nebo neexistují alternativy
        """
        # 1. Input validace
        if not sukl_code or not sukl_code.strip():
            raise SUKLValidationError("SÚKL kód nesmí být prázdný")

        sukl_code = sukl_code.strip()

        if not sukl_code.isdigit():
            raise SUKLValidationError(f"SÚKL kód musí být číselný (zadáno: {sukl_code})")

        if len(sukl_code) > 7:
            raise SUKLValidationError(
                f"SÚKL kód příliš dlouhý: {len(sukl_code)} znaků (maximum: 7)"
            )

        if not (1 <= limit <= 100):
            raise SUKLValidationError(f"Limit musí být 1-100 (zadáno: {limit})")

        # 2. Inicializace
        if not self._initialized:
            await self.initialize()

        # 3. Získej originální lék
        df_medicines = self._loader.get_table("dlp_lecivepripravky")
        if df_medicines is None:
            return []

        # Normalizuj kód (odstranění nul na začátku)
        sukl_code_norm = str(int(sukl_code)) if sukl_code.isdigit() else sukl_code

        original_mask = df_medicines["KOD_SUKL"].astype(str) == sukl_code_norm
        original_records = df_medicines[original_mask]

        if original_records.empty:
            return []  # Lék neexistuje

        original = original_records.iloc[0].to_dict()

        # 4. Zkontroluj dostupnost
        availability = self._normalize_availability(original.get("DODAVKY"))

        # Import zde aby se předešlo circular dependency
        from sukl_mcp.models import AvailabilityStatus

        if availability == AvailabilityStatus.AVAILABLE:
            return []  # Lék je dostupný → žádné alternativy nejsou potřeba

        # 5. Strategy A: Hledání podle stejné účinné látky
        candidates = []

        df_composition = self._loader.get_table("dlp_slozeni")
        if df_composition is not None:
            # Získej kódy účinných látek z originálního léku
            comp_mask = df_composition["KOD_SUKL"].astype(str) == sukl_code_norm
            original_composition = df_composition[comp_mask]

            if not original_composition.empty:
                substance_codes = original_composition["KOD_LATKY"].unique().tolist()

                # Najdi všechny léky obsahující tyto látky
                for substance_code in substance_codes:
                    subs_mask = df_composition["KOD_LATKY"] == substance_code
                    matching_sukl_codes = df_composition[subs_mask]["KOD_SUKL"].unique()

                    # Filtruj léčiva
                    med_mask = df_medicines["KOD_SUKL"].isin(matching_sukl_codes)
                    matching_medicines = df_medicines[med_mask]

                    if not matching_medicines.empty:
                        candidates.extend(matching_medicines.to_dict("records"))

                # Deduplikace (pokud je více látek, může být duplicita)
                seen = set()
                unique_candidates = []
                for cand in candidates:
                    cand_code = str(cand.get("KOD_SUKL"))
                    if cand_code not in seen:
                        seen.add(cand_code)
                        unique_candidates.append(cand)
                candidates = unique_candidates

        # 6. Strategy B: Fallback na ATC skupinu (pokud Strategy A nenašla nic)
        if not candidates:
            atc_code = original.get("ATC_WHO", "")
            if atc_code and len(atc_code) >= 3:
                atc_prefix = atc_code[:3]
                # Najdi léky se stejným ATC prefixem
                atc_mask = df_medicines["ATC_WHO"].str.startswith(atc_prefix, na=False)
                atc_results = df_medicines[atc_mask]

                if not atc_results.empty:
                    candidates = atc_results.to_dict("records")

        if not candidates:
            return []  # Žádné kandidáty nenalezeny

        # 7. Filtruj kandidáty
        filtered = []
        for candidate in candidates:
            # Vynech originální lék
            if str(candidate.get("KOD_SUKL")) == sukl_code_norm:
                continue

            # Pouze dostupné léky
            cand_availability = self._normalize_availability(candidate.get("DODAVKY"))
            if cand_availability != AvailabilityStatus.AVAILABLE:
                continue

            filtered.append(candidate)

        if not filtered:
            return []  # Žádné dostupné alternativy

        # 8. Rankuj alternativy
        ranked = self._rank_alternatives(filtered, original)

        # 9. Limituj výsledky
        top_alternatives = ranked[:limit]

        # 10. Obohať o cenové údaje
        enriched = await self._enrich_with_price_data(top_alternatives)

        # 11. Přidej metadata o důvodu matchování
        for alt in enriched:
            # Pokud používáme substance match, přidej match_reason
            if not candidates or len(candidates) > 0:
                # První kandidáti jsou substance match (pokud existují)
                if df_composition is not None and not original_composition.empty:
                    alt["match_reason"] = "Same active substance"
                else:
                    alt["match_reason"] = "Same ATC group"

        return enriched

    async def _enrich_with_price_data(self, results: list[dict]) -> list[dict]:
        """
        Obohať výsledky vyhledávání o cenové údaje z dlp_cau.

        Args:
            results: Seznam výsledků vyhledávání

        Returns:
            Výsledky obohacené o cenové údaje (has_reimbursement, max_price, patient_copay)
        """
        if not results:
            return results

        df_cau = self._loader.get_table("dlp_cau")
        if df_cau is None:
            # Pokud dlp_cau není k dispozici, vrať results s None hodnotami
            logger.warning(
                "⚠️  CENOVÁ DATA NEDOSTUPNÁ: dlp_cau.csv není v SÚKL Open Data. "
                "Ceny a úhrady budou null. "
                "TODO: Zjistit správný zdroj cenových dat."
            )
            for result in results:
                result["has_reimbursement"] = False
                result["max_price"] = None
                result["patient_copay"] = None
            return results

        # Import price calculator
        from sukl_mcp.price_calculator import get_price_data

        # Extrahuj všechny SÚKL kódy z výsledků
        sukl_codes = [str(r.get("KOD_SUKL", "")) for r in results if r.get("KOD_SUKL")]

        # Vytvoř lookup dictionary pro rychlé vyhledávání
        price_lookup = {}
        for sukl_code in sukl_codes:
            if sukl_code and sukl_code.isdigit():
                price_data = get_price_data(df_cau, sukl_code)
                if price_data:
                    price_lookup[sukl_code] = price_data

        # Obohať každý výsledek o cenové údaje
        for result in results:
            sukl_code = str(result.get("KOD_SUKL", ""))
            price_data = price_lookup.get(sukl_code)

            if price_data:
                result["has_reimbursement"] = price_data.get("is_reimbursed", False)
                result["max_price"] = price_data.get("max_price")
                result["patient_copay"] = price_data.get("patient_copay")
            else:
                result["has_reimbursement"] = False
                result["max_price"] = None
                result["patient_copay"] = None

        return results

    async def get_medicine_detail(self, sukl_code: str | int) -> dict | None:
        """Získej detail léčivého přípravku."""
        # Input validace - konverze na string
        sukl_code = str(sukl_code).strip() if sukl_code is not None else ""
        if not sukl_code:
            raise SUKLValidationError("SÚKL kód nesmí být prázdný")
        if not sukl_code.isdigit():
            raise SUKLValidationError(f"SÚKL kód musí být číselný (zadáno: {sukl_code})")
        if len(sukl_code) > 7:
            raise SUKLValidationError(
                f"SÚKL kód příliš dlouhý: {len(sukl_code)} znaků (maximum: 7)"
            )

        if not self._initialized:
            await self.initialize()

        df = self._loader.get_table("dlp_lecivepripravky")
        if df is None:
            return None

        # Převeď kód na string a odstraň nuly na začátku pro porovnání
        sukl_code_normalized = str(int(sukl_code)) if sukl_code.isdigit() else sukl_code

        result = df[df["KOD_SUKL"].astype(str) == sukl_code_normalized]
        if result.empty:
            return None

        row_dict = result.iloc[0].to_dict()
        return cast(dict[Any, Any], row_dict)

    async def get_composition(self, sukl_code: str | int) -> list[dict[Any, Any]]:
        """Získej složení léčivého přípravku."""
        if not self._initialized:
            await self.initialize()

        df_composition = self._loader.get_table("dlp_slozeni")
        if df_composition is None:
            return []

        # Normalizuj kód (podporuje int i string)
        sukl_code_str = str(sukl_code).strip()
        sukl_code_normalized = str(int(sukl_code_str)) if sukl_code_str.isdigit() else sukl_code_str
        results = df_composition[df_composition["KOD_SUKL"].astype(str) == sukl_code_normalized]
        records = results.to_dict("records")
        return cast(list[dict[Any, Any]], records)

    async def search_pharmacies(
        self,
        city: str | None = None,
        postal_code: str | None = None,
        has_24h: bool = False,
        has_internet_sales: bool = False,
        limit: int = 20,
    ) -> list[dict]:
        """
        Vyhledej lékárny podle kritérií.

        Args:
            city: Název města (case-insensitive)
            postal_code: PSČ (5 číslic)
            has_24h: Pouze lékárny s pohotovostí
            has_internet_sales: Pouze lékárny se zásilkovým prodejem
            limit: Max počet výsledků

        Returns:
            Seznam lékáren jako dict records
        """
        if not self._initialized:
            await self.initialize()

        df = self._loader.get_table("lekarny_seznam")
        if df is None:
            logger.warning("Tabulka lekarny_seznam není načtena")
            return []

        # Kopie pro filtrování
        results = df.copy()

        # Filtr podle města
        if city:
            city_upper = city.upper().strip()
            results = results[
                results["MESTO"].str.upper().str.contains(city_upper, na=False, regex=False)
            ]

        # Filtr podle PSČ
        if postal_code:
            psc_clean = postal_code.replace(" ", "").strip()
            results = results[
                results["PSC"].astype(str).str.replace(" ", "", regex=False) == psc_clean
            ]

        # Filtr podle pohotovosti
        if has_24h:
            # POHOTOVOST sloupec může být prázdný nebo obsahovat text
            results = results[results["POHOTOVOST"].notna() & (results["POHOTOVOST"].str.len() > 0)]

        # Filtr podle zásilkového prodeje
        if has_internet_sales:
            results = results[results["ZASILKOVY_PRODEJ"].str.upper() == "ANO"]

        # Limit
        results = results.head(limit)

        # Konverze na standardní formát pro server.py
        output = []
        for _, row in results.iterrows():
            # Bezpečné získání hodnot s kontrolou NA
            pohotovost = row.get("POHOTOVOST")
            zasilkovy = str(row.get("ZASILKOVY_PRODEJ", ""))

            output.append(
                {
                    "ID_LEKARNY": row.get("KOD_LEKARNY", ""),
                    "NAZEV": row.get("NAZEV", ""),
                    "ULICE": row.get("ULICE", ""),
                    "MESTO": row.get("MESTO", ""),
                    "PSC": str(row.get("PSC", "")).replace(" ", ""),
                    "OKRES": None,  # Není v datech
                    "KRAJ": None,  # Není v datech
                    "TELEFON": row.get("TELEFON", ""),
                    "EMAIL": row.get("EMAIL", ""),
                    "WEB": row.get("WWW", ""),
                    "lat": None,  # Není v datech
                    "lon": None,  # Není v datech
                    "PROVOZOVATEL": None,
                    "nepretrzity_provoz": "ano" if pd.notna(pohotovost) and pohotovost else None,
                    "internetovy_prodej": "ano" if zasilkovy.upper() == "ANO" else None,
                    "pripravna": None,
                    "aktivni": "ano",
                }
            )

        return output

    async def get_atc_groups(self, atc_prefix: str | None = None, limit: int = 100) -> list[dict]:
        """Získej ATC skupiny podle prefixu."""
        # Input validace
        if atc_prefix:
            atc_prefix = atc_prefix.strip()
            if len(atc_prefix) > 7:
                raise SUKLValidationError(
                    f"ATC prefix příliš dlouhý: {len(atc_prefix)} znaků (maximum: 7)"
                )

        if not self._initialized:
            await self.initialize()

        df = self._loader.get_table("dlp_atc")
        if df is None:
            return []

        # Pokud je zadán prefix, filtruj podle něj
        if atc_prefix:
            results = df[df["ATC"].str.startswith(atc_prefix, na=False)]
        else:
            results = df

        # Vrať omezený počet výsledků (pokud limit > 0)
        if limit > 0:
            results = results.head(limit)

        records = results.to_dict("records")
        return cast(list[dict[Any, Any]], records)

    async def get_price_info(self, sukl_code: str) -> dict | None:
        """
        Získej cenové a úhradové informace o léčivém přípravku.

        Args:
            sukl_code: SÚKL kód léčiva

        Returns:
            Dict s cenovými údaji nebo None
        """
        # Input validace
        if not sukl_code or not sukl_code.strip():
            raise SUKLValidationError("SÚKL kód nesmí být prázdný")
        sukl_code = sukl_code.strip()
        if not sukl_code.isdigit():
            raise SUKLValidationError(f"SÚKL kód musí být číselný (zadáno: {sukl_code})")
        if len(sukl_code) > 7:
            raise SUKLValidationError(
                f"SÚKL kód příliš dlouhý: {len(sukl_code)} znaků (maximum: 7)"
            )

        if not self._initialized:
            await self.initialize()

        df_cau = self._loader.get_table("dlp_cau")
        if df_cau is None:
            logger.warning("dlp_cau table není načtena - cenové údaje nejsou dostupné")
            return None

        # Použij price_calculator pro získání dat
        from sukl_mcp.price_calculator import get_price_data

        return get_price_data(df_cau, sukl_code)

    async def close(self) -> None:
        """Uzavři klienta."""
        logger.info("Uzavírám SÚKL klienta...")
        self._initialized = False


# Globální instance klienta s thread-safe inicializací
_client: SUKLClient | None = None
_client_lock: asyncio.Lock = asyncio.Lock()


async def get_sukl_client() -> SUKLClient:
    """Získej globální instanci SÚKL klienta (thread-safe)."""
    global _client

    # Rychlá kontrola bez zámku (double-checked locking)
    if _client is not None:
        return _client

    # Kritická sekce - zajištění jediné instance
    async with _client_lock:
        # Opětovná kontrola v zámku
        if _client is None:
            _client = SUKLClient()
            await _client.initialize()

    return _client


async def close_sukl_client() -> None:
    """Uzavři globální instanci SÚKL klienta."""
    global _client
    if _client:
        await _client.close()
        _client = None
