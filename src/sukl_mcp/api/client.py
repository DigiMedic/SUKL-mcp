# Klientský kód s opravami pro SUKLAPIClient
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from pydantic import ValidationError

from .rest_models import (
    DLPResponse,
    LekarnyResponse,
    Lekarna,
    CiselnikResponse,
    DatumAktualizace,
    DLPSearchParams,
)
from ..exceptions import SUKLAPIError, SUKLValidationError

logger = logging.getLogger(__name__)


@dataclass
class SUKLAPIConfig:
    """Konfigurace SÚKL API klienta."""

    base_url: str = "https://prehledy.sukl.cz/prehledy/v1"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    cache_ttl: int = 300
    rate_limit: int = 60
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


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
    REST API klient pro prehledy.sukl.cz/v1.
    """

    def __init__(self, config: SUKLAPIConfig | None = None):
        self.config = config or SUKLAPIConfig()
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[str, CacheEntry] = {}
        self._request_count: int = 0
        self._rate_limit_reset: float = 0
        self._closed: bool = False

    async def __aenter__(self):
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def _ensure_client(self):
        if self._client is None or self._closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "User-Agent": self.config.user_agent,
                },
                follow_redirects=True,
            )
            self._closed = False
            logger.info(f"HTTP client initialized: {self.config.base_url}")

    async def close(self):
        if self._client and not self._closed:
            await self._client.aclose()
            self._client = None
            self._closed = True
            logger.info("HTTP client closed")

    async def _check_rate_limit(self):
        now = time.time()
        if now - self._rate_limit_reset > 60:
            self._request_count = 0
            self._rate_limit_reset = now
        if self._request_count >= self.config.rate_limit:
            wait_time = 60 - (now - self._rate_limit_reset) + 0.1
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
            self._request_count = 0
            self._rate_limit_reset = time.time()
        self._request_count += 1

    def _get_cache_key(
        self, method: str, endpoint: str, params: dict | None, json_data: dict | None
    ) -> str:
        params_str = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
        json_str = (
            "&".join(f"{k}={v}" for k, v in sorted((json_data or {}).items())) if json_data else ""
        )
        return f"{method}:{endpoint}?{params_str}&{json_str}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json_data: dict | None = None,
        use_cache: bool = True,
    ) -> Any:
        await self._ensure_client()
        await self._check_rate_limit()
        cache_key = self._get_cache_key(method, endpoint, params, json_data)
        if use_cache and cache_key in self._cache:
            entry = self._cache[cache_key]
            if entry.is_valid(self.config.cache_ttl):
                logger.debug(f"Cache hit: {endpoint}")
                return entry.data

        last_error: Exception | None = None
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(
                    f"API request [{attempt + 1}/{self.config.max_retries}]: {method} {endpoint}"
                )
                assert self._client is not None, "Client not initialized"
                response = await self._client.request(
                    method, endpoint, params=params, json=json_data
                )

                if response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    if "kodChyby" in error_data:
                        api_error = error_data
                        raise SUKLAPIError(
                            f"API error {api_error['kodChyby']}: {api_error['popisChyby']}",
                            status_code=api_error["kodChyby"],
                        )
                    response.raise_for_status()

                data = response.json()
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

            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay * (2**attempt)
                logger.info(f"Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)

        if cache_key in self._cache:
            logger.warning(f"Using stale cache after {self.config.max_retries} failures")
            return self._cache[cache_key].data

        raise SUKLAPIError(
            f"API request failed after {self.config.max_retries} attempts"
        ) from last_error

    async def _get(self, endpoint: str, params: dict | None = None, use_cache: bool = True) -> Any:
        return await self._request("GET", endpoint, params, use_cache=use_cache)

    async def search_medicines(
        self,
        atc: str | None = None,
        stav_registrace: str | None = None,
        uhrada: str | None = None,
        je_dodavka: bool | None = None,
        je_regulovany: bool | None = None,
        stranka: int = 1,
        pocet: int = 10,
    ) -> DLPResponse:
        params = DLPSearchParams(
            atc=atc,
            stavRegistrace=stav_registrace,
            uhrada=uhrada,
            jeDodavka=je_dodavka,
            jeRegulovany=je_regulovany,
            stranka=stranka,
            pocet=pocet,
        )
        request_data = params.model_dump(exclude_none=True)
        response_data = await self._request("POST", "/dlprc", json_data=request_data)
        try:
            return DLPResponse(**response_data)
        except ValidationError as e:
            raise SUKLValidationError(f"Invalid API response: {e}")

    async def get_pharmacies(
        self,
        stranka: int = 1,
        pocet: int = 10,
    ) -> LekarnyResponse:
        params = {"stranka": stranka, "pocet": pocet}
        response_data = await self._get("/lekarny", params)
        try:
            return LekarnyResponse(**response_data)
        except ValidationError as e:
            raise SUKLValidationError(f"Invalid API response: {e}")

    async def get_pharmacy_detail(self, kod_lekarny: str) -> Lekarna:
        response_data = await self._get(f"/lekarny/{kod_lekarny}")
        try:
            return Lekarna(**response_data)
        except ValidationError as e:
            raise SUKLValidationError(f"Invalid API response: {e}")

    async def get_ciselnik(self, nazev: str) -> list[Any]:
        response_data = await self._get(f"/ciselniky/{nazev}")
        if isinstance(response_data, list):
            return response_data
        return []

    async def get_atc_codes(self) -> list[Any]:
        response_data = await self._get("/ciselniky/latky")
        if isinstance(response_data, list):
            return response_data
        return []

    async def get_update_dates(self) -> DatumAktualizace:
        response_data = await self._get("/datum-aktualizace")
        try:
            return DatumAktualizace(**response_data)
        except ValidationError as e:
            raise SUKLValidationError(f"Invalid API response: {e}")

    def clear_cache(self):
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared ({count} entries)")

    def get_cache_stats(self) -> dict[str, int]:
        valid = sum(1 for e in self._cache.values() if e.is_valid(self.config.cache_ttl))
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid,
            "stale_entries": len(self._cache) - valid,
        }

    async def health_check(self) -> dict[str, Any]:
        try:
            start = time.time()
            pharmacies = await self.get_pharmacies(stranka=1, pocet=1)
            latency = (time.time() - start) * 1000
            return {
                "status": "healthy" if pharmacies.celkem > 0 else "degraded",
                "api_available": True,
                "latency_ms": round(latency, 2),
                "cache_stats": self.get_cache_stats(),
                "sample_pharmacy": pharmacies.data[0].nazev if pharmacies.data else None,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_available": False,
                "error": str(e),
                "cache_stats": self.get_cache_stats(),
            }


_api_client: SUKLAPIClient | None = None
_client_lock: asyncio.Lock = asyncio.Lock()


async def get_rest_client() -> SUKLAPIClient:
    global _api_client
    if _api_client is None:
        async with _client_lock:
            if _api_client is None:
                _api_client = SUKLAPIClient()
    return _api_client


async def close_rest_client() -> None:
    global _api_client
    if _api_client:
        await _api_client.close()
        _api_client = None
