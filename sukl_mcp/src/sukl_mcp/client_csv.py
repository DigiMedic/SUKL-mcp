"""
CSV-based klient pro SÚKL Open Data.

Načítá data z DLP CSV souborů a poskytuje in-memory vyhledávání.
"""

import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SUKLConfig(BaseModel):
    """Konfigurace SÚKL klienta."""

    # Open Data URL
    opendata_dlp_url: str = "https://opendata.sukl.cz/soubory/SOD20251223/DLP20251223.zip"

    # Local cache
    cache_dir: Path = Path("/tmp/sukl_dlp_cache")
    data_dir: Path = Path("/tmp/sukl_dlp_data")

    # Download timeout
    download_timeout: float = 120.0


class SUKLDataLoader:
    """Loader pro SÚKL CSV data."""

    def __init__(self, config: Optional[SUKLConfig] = None):
        self.config = config or SUKLConfig()
        self._data: dict[str, pd.DataFrame] = {}
        self._loaded = False

    async def load_data(self) -> None:
        """Stáhni a načti DLP data."""
        if self._loaded:
            logger.info("Data již načtena")
            return

        logger.info("Načítám SÚKL DLP data...")

        # Vytvořím adresáře
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

        # Stáhni ZIP pokud neexistuje
        zip_path = self.config.cache_dir / "DLP.zip"
        if not zip_path.exists():
            await self._download_zip(zip_path)

        # Rozbal ZIP
        if not (self.config.data_dir / "dlp_lecivepripravky.csv").exists():
            self._extract_zip(zip_path)

        # Načti klíčové CSV soubory
        await self._load_csvs()

        self._loaded = True
        logger.info(f"Data načtena: {len(self._data)} tabulek")

    async def _download_zip(self, zip_path: Path) -> None:
        """Stáhni DLP ZIP soubor."""
        logger.info(f"Stahuji {self.config.opendata_dlp_url}...")

        async with httpx.AsyncClient(timeout=self.config.download_timeout) as client:
            async with client.stream('GET', self.config.opendata_dlp_url) as resp:
                resp.raise_for_status()

                with open(zip_path, 'wb') as f:
                    async for chunk in resp.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

        logger.info(f"Staženo: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")

    def _extract_zip(self, zip_path: Path) -> None:
        """Rozbal ZIP soubor."""
        logger.info(f"Rozbaluji {zip_path}...")

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.config.data_dir)

        logger.info(f"Rozbaleno do {self.config.data_dir}")

    async def _load_csvs(self) -> None:
        """Načti CSV soubory do pandas DataFrames."""
        logger.info("Načítám CSV soubory...")

        # Klíčové tabulky
        tables = [
            'dlp_lecivepripravky',  # Hlavní tabulka léčiv
            'dlp_slozeni',          # Složení
            'dlp_lecivelatky',      # Léčivé látky
            'dlp_atc',              # ATC kódy
            'dlp_nazvydokumentu',   # Dokumenty (PIL)
        ]

        for table in tables:
            csv_path = self.config.data_dir / f"{table}.csv"
            if csv_path.exists():
                df = pd.read_csv(
                    csv_path,
                    sep=';',
                    encoding='cp1250',
                    low_memory=False
                )
                self._data[table] = df
                logger.info(f"  ✓ {table}: {len(df)} záznamů")
            else:
                logger.warning(f"  ✗ {table}: soubor nenalezen")

    def get_table(self, name: str) -> Optional[pd.DataFrame]:
        """Získej DataFrame tabulky."""
        return self._data.get(name)


class SUKLClient:
    """Async klient pro SÚKL CSV data."""

    def __init__(self, config: Optional[SUKLConfig] = None):
        self.config = config or SUKLConfig()
        self._loader = SUKLDataLoader(config)
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

    async def search_medicines(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        only_available: bool = False,
        only_reimbursed: bool = False,
    ) -> list[dict]:
        """Vyhledej léčivé přípravky podle názvu."""
        if not self._initialized:
            await self.initialize()

        df = self._loader.get_table('dlp_lecivepripravky')
        if df is None:
            return []

        # Case-insensitive vyhledávání v názvu
        mask = df['NAZEV'].str.contains(query, case=False, na=False)
        results = df[mask]

        # Aplikuj filtry
        if only_available:
            # TODO: přidat filtr dostupnosti
            pass

        if only_reimbursed:
            # TODO: přidat filtr úhrad
            pass

        # Paging
        results = results.iloc[offset:offset + limit]

        # Konverze na dict
        return results.to_dict('records')

    async def get_medicine_detail(self, sukl_code: str) -> Optional[dict]:
        """Získej detail léčivého přípravku."""
        if not self._initialized:
            await self.initialize()

        df = self._loader.get_table('dlp_lecivepripravky')
        if df is None:
            return None

        # Převeď kód na string a odstraň nuly na začátku pro porovnání
        sukl_code_normalized = str(int(sukl_code)) if sukl_code.isdigit() else sukl_code

        result = df[df['KOD_SUKL'].astype(str) == sukl_code_normalized]
        if result.empty:
            return None

        return result.iloc[0].to_dict()

    async def get_composition(self, sukl_code: str) -> list[dict]:
        """Získej složení léčivého přípravku."""
        if not self._initialized:
            await self.initialize()

        df_composition = self._loader.get_table('dlp_slozeni')
        if df_composition is None:
            return []

        # Normalizuj kód
        sukl_code_normalized = str(int(sukl_code)) if sukl_code.isdigit() else sukl_code
        results = df_composition[df_composition['KOD_SUKL'].astype(str) == sukl_code_normalized]
        return results.to_dict('records')

    async def search_pharmacies(
        self,
        city: Optional[str] = None,
        postal_code: Optional[str] = None,
        has_24h: bool = False,
        has_internet_sales: bool = False,
        limit: int = 20,
    ) -> list[dict]:
        """Vyhledej lékárny podle kritérií."""
        if not self._initialized:
            await self.initialize()

        # Pro teď vrátíme prázdný seznam, protože nemáme data o lékárnách v DLP
        logger.warning("Vyhledávání lékáren není implementováno - DLP neobsahuje data o lékárnách")
        return []

    async def get_atc_groups(self, atc_prefix: Optional[str] = None) -> list[dict]:
        """Získej ATC skupiny podle prefixu."""
        if not self._initialized:
            await self.initialize()

        df = self._loader.get_table('dlp_atc')
        if df is None:
            return []

        # Pokud je zadán prefix, filtruj podle něj
        if atc_prefix:
            results = df[df['ATC'].str.startswith(atc_prefix, na=False)]
        else:
            results = df

        # Vrať max 100 výsledků
        return results.head(100).to_dict('records')

    async def close(self) -> None:
        """Uzavři klienta."""
        logger.info("Uzavírám SÚKL klienta...")
        self._initialized = False


# Globální instance klienta
_client: Optional[SUKLClient] = None


async def get_sukl_client() -> SUKLClient:
    """Získej globální instanci SÚKL klienta."""
    global _client
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
