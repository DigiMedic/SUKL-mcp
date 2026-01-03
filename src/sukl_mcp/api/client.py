"""
SÚKL API Client - Unified async klient pro SÚKL REST API.

Poskytuje:
- Async HTTP komunikaci s retry logikou
- In-memory caching s TTL
- Rate limiting
- Structured logging
- Fallback na cache při nedostupnosti

Použití:
    async with SUKLAPIClient() as client:
        # Vyhledávání
        codes = await client.search_medicines("ibuprofen")

        # Detail léčiva
        medicine = await client.get_medicine("0254045")

        # S custom konfigurací
        config = SUKLAPIConfig(timeout=60.0, cache_ttl=600)
        async with SUKLAPIClient(config) as client:
            ...
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

import httpx
from pydantic import BaseModel

from sukl_mcp.api.models import (
    APIError,
    APILecivyPripravek,
    APISearchResponse,
)
from sukl_mcp.exceptions import SUKLAPIError, SUKLValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class SUKLAPIConfig:
    """
    Konfigurace SÚKL API klienta.

    Attributes:
        base_url: Základní URL SÚKL API
        timeout: Timeout pro HTTP requesty (sekundy)
        max_retries: Maximální počet pokusů při chybě
        retry_delay: Základní delay mezi pokusy (sekundy)
        cache_ttl: TTL pro cache (sekundy)
        rate_limit: Max requestů za minutu
        user_agent: User-Agent header
    """

    base_url: str = "https://prehledy.sukl.cz"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    cache_ttl: int = 300  # 5 minut
    rate_limit: int = 60  # requests/minute
    user_agent: str = "SUKL-MCP/4.0 (Python httpx)"


@dataclass
class CacheEntry:
    """Položka v cache."""

    data: Any
    timestamp: float

    def is_valid(self, ttl: int) -> bool:
        """Zkontroluje, zda je cache stále platná."""
        return (time.time() - self.timestamp) < ttl


class SUKLAPIClient:
    """
    Unified async klient pro SÚKL REST API.

    Features:
    - Async context manager pro správu HTTP session
    - Automatický retry s exponential backoff
    - In-memory cache s TTL
    - Rate limiting
    - Structured logging

    Endpoints:
    - /dlp/v1/lecive-pripravky - Léčivé přípravky
    - /dlp/v1/lecive-pripravky/{kod} - Detail léčiva
    - /lka/v1/lekarny - Lékárny (pokud existuje)
    """

    def __init__(self, config: SUKLAPIConfig | None = None):
        """
        Inicializace klienta.

        Args:
            config: Konfigurace klienta (volitelné)
        """
        self.config = config or SUKLAPIConfig()
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[str, CacheEntry] = {}
        self._request_count: int = 0
        self._rate_limit_reset: float = 0
        self._closed: bool = False

    async def __aenter__(self) -> "SUKLAPIClient":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> None:
        """Zajistí, že HTTP klient je inicializovaný."""
        if self._client is None or self._closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "Accept": "application/json",
                    "User-Agent": self.config.user_agent,
                },
                follow_redirects=True,
            )
            self._closed = False
            logger.info(f"HTTP client initialized: {self.config.base_url}")

    async def close(self) -> None:
        """Uzavře HTTP klienta a vyčistí resources."""
        if self._client and not self._closed:
            await self._client.aclose()
            self._closed = True
            logger.info("HTTP client closed")

    # === Core HTTP Methods ===

    async def _check_rate_limit(self) -> None:
        """Kontroluje a vynucuje rate limit."""
        now = time.time()

        # Reset počítadla každou minutu
        if now - self._rate_limit_reset > 60:
            self._request_count = 0
            self._rate_limit_reset = now

        # Čekej pokud jsme na limitu
        if self._request_count >= self.config.rate_limit:
            wait_time = 60 - (now - self._rate_limit_reset) + 0.1
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                self._request_count = 0
                self._rate_limit_reset = time.time()

        self._request_count += 1

    def _get_cache_key(self, method: str, endpoint: str, params: dict | None) -> str:
        """Vytvoří cache klíč."""
        params_str = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
        return f"{method}:{endpoint}?{params_str}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        use_cache: bool = True,
    ) -> Any:
        """
        Provede HTTP request s retry a caching.

        Args:
            method: HTTP metoda (GET, POST, ...)
            endpoint: API endpoint (např. /dlp/v1/lecive-pripravky)
            params: Query parametry
            use_cache: Použít cache (default True)

        Returns:
            Parsed JSON response

        Raises:
            SUKLAPIError: Při chybě API
        """
        await self._ensure_client()

        # Rate limiting
        await self._check_rate_limit()

        # Cache check
        cache_key = self._get_cache_key(method, endpoint, params)
        if use_cache and cache_key in self._cache:
            entry = self._cache[cache_key]
            if entry.is_valid(self.config.cache_ttl):
                logger.debug(f"Cache hit: {endpoint}")
                return entry.data

        # Retry loop
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(
                    f"API request [{attempt + 1}/{self.config.max_retries}]: {method} {endpoint}"
                )

                response = await self._client.request(method, endpoint, params=params)  # type: ignore

                # Handle errors
                if response.status_code >= 400:
                    error_data = response.json()
                    if "kodChyby" in error_data:
                        api_error = APIError(**error_data)
                        raise SUKLAPIError(
                            f"API error {api_error.kodChyby}: {api_error.popisChyby}"
                        )
                    response.raise_for_status()

                data = response.json()

                # Update cache
                if use_cache:
                    self._cache[cache_key] = CacheEntry(data=data, timestamp=time.time())

                return data

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(f"HTTP error {e.response.status_code}: {endpoint}")
                if e.response.status_code < 500:
                    raise SUKLAPIError(f"HTTP {e.response.status_code}: {endpoint}") from e

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"Timeout: {endpoint}")

            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Request error: {e}")

            # Exponential backoff
            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay * (2**attempt)
                logger.info(f"Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)

        # All retries failed - try cache fallback
        if cache_key in self._cache:
            logger.warning(f"Using stale cache after {self.config.max_retries} failures")
            return self._cache[cache_key].data

        raise SUKLAPIError(
            f"API request failed after {self.config.max_retries} attempts"
        ) from last_error

    async def _get(self, endpoint: str, params: dict | None = None, use_cache: bool = True) -> Any:
        """HTTP GET request."""
        return await self._request("GET", endpoint, params, use_cache)

    # === Léčivé přípravky ===

    async def search_medicines(
        self,
        query: str,
        typ_seznamu: Literal["dlpo", "scau", "scup", "sneh", "splp", "vpois"] = "dlpo",
        limit: int | None = None,
    ) -> APISearchResponse:
        """
        Vyhledá léčivé přípravky podle názvu.

        Args:
            query: Hledaný text (název, část názvu)
            typ_seznamu: Typ seznamu (dlpo = léčivé přípravky)
            limit: Maximální počet výsledků (None = všechny)

        Returns:
            APISearchResponse se seznamem SÚKL kódů

        Note:
            SÚKL API vrací pouze kódy, pro detaily použijte get_medicine()
        """
        if not query or not query.strip():
            raise SUKLValidationError("Dotaz nesmí být prázdný")

        params = {
            "nazev": query.strip(),
            "typSeznamu": typ_seznamu,
        }

        data = await self._get("/dlp/v1/lecive-pripravky", params)

        # API vrací seznam kódů
        codes = data if isinstance(data, list) else []

        # Limit výsledků
        if limit and len(codes) > limit:
            codes = codes[:limit]

        return APISearchResponse(codes=codes, total=len(data) if isinstance(data, list) else 0)

    async def get_medicine(self, sukl_code: str) -> APILecivyPripravek | None:
        """
        Získá detail léčivého přípravku podle SÚKL kódu.

        Args:
            sukl_code: SÚKL kód (7 číslic, např. "0254045")

        Returns:
            APILecivyPripravek nebo None pokud nenalezeno
        """
        # Validace kódu
        code = sukl_code.strip().zfill(7)
        if not code.isdigit() or len(code) != 7:
            raise SUKLValidationError(f"Neplatný SÚKL kód: {sukl_code}")

        try:
            data = await self._get(f"/dlp/v1/lecive-pripravky/{code}")
            return APILecivyPripravek(**data)
        except SUKLAPIError as e:
            if "404" in str(e):
                return None
            raise

    async def get_medicines_batch(
        self,
        sukl_codes: list[str],
        max_concurrent: int = 5,
    ) -> list[APILecivyPripravek]:
        """
        Získá detaily pro více léčiv paralelně.

        Args:
            sukl_codes: Seznam SÚKL kódů
            max_concurrent: Max paralelních requestů

        Returns:
            Seznam nalezených léčiv
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_one(code: str) -> APILecivyPripravek | None:
            async with semaphore:
                return await self.get_medicine(code)

        results = await asyncio.gather(
            *[fetch_one(code) for code in sukl_codes], return_exceptions=True
        )

        return [r for r in results if isinstance(r, APILecivyPripravek)]

    # === Dostupnost ===

    async def check_availability(self, sukl_code: str) -> bool:
        """
        Zkontroluje, zda je léčivo aktuálně dodáváno.

        Args:
            sukl_code: SÚKL kód

        Returns:
            True pokud je dodáváno
        """
        medicine = await self.get_medicine(sukl_code)
        return medicine.jeDodavka if medicine else False

    # === Utility ===

    def clear_cache(self) -> None:
        """Vymaže cache."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared ({count} entries)")

    def get_cache_stats(self) -> dict[str, int]:
        """Vrátí statistiky cache."""
        time.time()
        valid = sum(1 for e in self._cache.values() if e.is_valid(self.config.cache_ttl))
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid,
            "stale_entries": len(self._cache) - valid,
        }

    async def health_check(self) -> dict[str, Any]:
        """
        Provede health check API.

        Returns:
            Dict s výsledky kontroly
        """
        try:
            # Zkusíme načíst detail známého léčiva
            start = time.time()
            medicine = await self.get_medicine("0254045")  # PARALEN
            latency = (time.time() - start) * 1000

            return {
                "status": "healthy" if medicine else "degraded",
                "api_available": True,
                "latency_ms": round(latency, 2),
                "cache_stats": self.get_cache_stats(),
                "sample_medicine": medicine.nazev if medicine else None,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_available": False,
                "error": str(e),
                "cache_stats": self.get_cache_stats(),
            }


# === Singleton pattern pro globální klient ===

_global_client: SUKLAPIClient | None = None


async def get_api_client() -> SUKLAPIClient:
    """Získá globální API klient (singleton)."""
    global _global_client
    if _global_client is None:
        _global_client = SUKLAPIClient()
        await _global_client._ensure_client()
    return _global_client


async def close_api_client() -> None:
    """Uzavře globální API klient."""
    global _global_client
    if _global_client:
        await _global_client.close()
        _global_client = None
