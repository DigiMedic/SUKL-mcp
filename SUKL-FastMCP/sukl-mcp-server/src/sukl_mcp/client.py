"""
HTTP klient pro komunikaci s SÚKL API a Open Data.

Podporuje:
- REST API (prehledy.sukl.cz)
- Open Data CSV stahování
- Cachování odpovědí
- Rate limiting
- Retry logiku
"""

import asyncio
import csv
import hashlib
import io
import logging
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CacheEntry(BaseModel):
    """Záznam v cache."""
    data: Any
    created_at: datetime
    expires_at: datetime
    hits: int = 0


class SUKLConfig(BaseModel):
    """Konfigurace SÚKL klienta."""
    # API URLs
    api_base_url: str = "https://prehledy.sukl.cz/prehledy/v1"
    opendata_base_url: str = "https://opendata.sukl.cz"
    
    # Timeouts
    timeout_seconds: float = 30.0
    connect_timeout: float = 10.0
    
    # Rate limiting
    max_requests_per_minute: int = 60
    request_delay_ms: int = 100
    
    # Cache
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600  # 1 hodina
    cache_dir: Optional[Path] = None
    max_cache_size_mb: int = 500
    
    # Retry
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    
    # CSV zpracování
    csv_encoding: str = "windows-1250"  # SÚKL používá win-1250
    csv_delimiter: str = ";"


class RateLimiter:
    """Jednoduchý rate limiter."""
    
    def __init__(self, max_requests: int, period_seconds: int = 60):
        self.max_requests = max_requests
        self.period = period_seconds
        self.requests: list[datetime] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Počkej dokud není možné poslat request."""
        async with self._lock:
            now = datetime.now()
            # Odstraň staré requesty
            cutoff = now - timedelta(seconds=self.period)
            self.requests = [r for r in self.requests if r > cutoff]
            
            if len(self.requests) >= self.max_requests:
                # Počkej na uvolnění
                wait_time = (self.requests[0] - cutoff).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            self.requests.append(now)


class MemoryCache:
    """In-memory cache s TTL."""
    
    def __init__(self, default_ttl: int = 3600, max_size_mb: int = 100):
        self._cache: dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size_mb * 1024 * 1024
        self._lock = asyncio.Lock()
    
    def _make_key(self, *args, **kwargs) -> str:
        """Vytvoř hash klíč z argumentů."""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Získej hodnotu z cache."""
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if datetime.now() > entry.expires_at:
                del self._cache[key]
                return None
            
            entry.hits += 1
            return entry.data
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Ulož hodnotu do cache."""
        async with self._lock:
            ttl = ttl or self._default_ttl
            self._cache[key] = CacheEntry(
                data=value,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(seconds=ttl)
            )
            await self._cleanup_if_needed()
    
    async def _cleanup_if_needed(self):
        """Vyčisti expirované záznamy."""
        now = datetime.now()
        expired = [k for k, v in self._cache.items() if now > v.expires_at]
        for key in expired:
            del self._cache[key]
    
    async def clear(self):
        """Vymaž celou cache."""
        async with self._lock:
            self._cache.clear()
    
    def stats(self) -> dict:
        """Vrať statistiky cache."""
        total_hits = sum(e.hits for e in self._cache.values())
        return {
            "entries": len(self._cache),
            "total_hits": total_hits,
        }


class SUKLClient:
    """
    Asynchronní HTTP klient pro SÚKL API a Open Data.
    
    Použití:
        async with SUKLClient() as client:
            results = await client.search_medicines("ibuprofen")
    """
    
    def __init__(self, config: Optional[SUKLConfig] = None):
        self.config = config or SUKLConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = RateLimiter(
            self.config.max_requests_per_minute
        )
        self._cache = MemoryCache(
            default_ttl=self.config.cache_ttl_seconds
        )
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def connect(self):
        """Inicializuj HTTP klienta."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    self.config.timeout_seconds,
                    connect=self.config.connect_timeout
                ),
                follow_redirects=True,
                headers={
                    "User-Agent": "SUKL-MCP-Server/1.0",
                    "Accept": "application/json",
                    "Accept-Language": "cs"
                }
            )
        logger.info("SÚKL client connected")
    
    async def close(self):
        """Uzavři HTTP klienta."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("SÚKL client closed")
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not connected. Use 'async with' or call connect()")
        return self._client
    
    # === REST API metody ===
    
    async def _api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        use_cache: bool = True
    ) -> dict:
        """Proveď API request s retry logikou."""
        url = urljoin(self.config.api_base_url + "/", endpoint.lstrip("/"))
        cache_key = self._cache._make_key(method, url, params)
        
        # Zkus cache
        if use_cache and self.config.cache_enabled:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {endpoint}")
                return cached
        
        # Rate limiting
        await self._rate_limiter.acquire()
        
        # Request s retry
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                if method.upper() == "GET":
                    response = await self.client.get(url, params=params)
                else:
                    response = await self.client.request(method, url, params=params)
                
                response.raise_for_status()
                data = response.json()
                
                # Ulož do cache
                if use_cache and self.config.cache_enabled:
                    await self._cache.set(cache_key, data)
                
                return data
                
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error {e.response.status_code}: {endpoint}")
                if e.response.status_code == 404:
                    raise
                last_error = e
                
            except httpx.RequestError as e:
                logger.warning(f"Request error (attempt {attempt+1}): {e}")
                last_error = e
            
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
        
        raise last_error or Exception("Request failed")
    
    async def search_medicines(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        only_available: bool = False,
        only_reimbursed: bool = False
    ) -> list[dict]:
        """
        Vyhledej léčivé přípravky.
        
        Args:
            query: Hledaný text (název, účinná látka, ATC)
            limit: Max počet výsledků
            offset: Offset pro stránkování
            only_available: Pouze dostupné přípravky
            only_reimbursed: Pouze hrazené přípravky
        """
        params = {
            "nazev": query,
            "limit": limit,
            "offset": offset
        }
        
        if only_available:
            params["dostupnost"] = "ano"
        if only_reimbursed:
            params["uhrada"] = "ano"
        
        try:
            response = await self._api_request("GET", "/leciva", params)
            return response.get("items", response) if isinstance(response, dict) else response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise
    
    async def get_medicine_detail(self, sukl_code: str) -> Optional[dict]:
        """Získej detail léčivého přípravku podle SÚKL kódu."""
        try:
            return await self._api_request("GET", f"/leciva/{sukl_code}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def search_pharmacies(
        self,
        city: Optional[str] = None,
        postal_code: Optional[str] = None,
        has_24h: bool = False,
        has_internet_sales: bool = False,
        limit: int = 50
    ) -> list[dict]:
        """Vyhledej lékárny."""
        params = {"limit": limit}
        
        if city:
            params["mesto"] = city
        if postal_code:
            params["psc"] = postal_code
        if has_24h:
            params["nepretrzity_provoz"] = "ano"
        if has_internet_sales:
            params["internetovy_prodej"] = "ano"
        
        try:
            response = await self._api_request("GET", "/lekarny", params)
            return response.get("items", response) if isinstance(response, dict) else response
        except httpx.HTTPStatusError:
            return []
    
    async def get_atc_groups(self, parent_code: Optional[str] = None) -> list[dict]:
        """Získej ATC skupiny."""
        params = {}
        if parent_code:
            params["nadrazena_skupina"] = parent_code
        
        try:
            response = await self._api_request("GET", "/atc", params)
            return response.get("items", response) if isinstance(response, dict) else response
        except httpx.HTTPStatusError:
            return []
    
    # === Open Data metody ===
    
    async def download_csv_dataset(
        self,
        dataset_name: str,
        extract_file: Optional[str] = None
    ) -> list[dict]:
        """
        Stáhni CSV dataset z Open Data.
        
        Args:
            dataset_name: Název datasetu (např. 'dlp', 'lekarny')
            extract_file: Konkrétní soubor ze ZIPu
        """
        cache_key = f"opendata_{dataset_name}_{extract_file or 'all'}"
        
        # Cache check
        if self.config.cache_enabled:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached
        
        # URL pro různé datasety
        urls = {
            "dlp": "/soubory/dlp.zip",
            "lekarny": "/soubory/lekarny.zip",
            "pil": "/soubory/pil.zip",
            "spc": "/soubory/spc.zip",
        }
        
        url = urls.get(dataset_name)
        if not url:
            raise ValueError(f"Neznámý dataset: {dataset_name}")
        
        full_url = urljoin(self.config.opendata_base_url, url)
        
        await self._rate_limiter.acquire()
        
        try:
            response = await self.client.get(full_url)
            response.raise_for_status()
            
            # Rozbal ZIP
            zip_buffer = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_buffer) as zf:
                data = []
                
                for filename in zf.namelist():
                    if extract_file and extract_file not in filename:
                        continue
                    if not filename.endswith('.csv'):
                        continue
                    
                    with zf.open(filename) as f:
                        # Dekóduj s win-1250
                        content = f.read().decode(self.config.csv_encoding, errors='replace')
                        reader = csv.DictReader(
                            io.StringIO(content),
                            delimiter=self.config.csv_delimiter
                        )
                        for row in reader:
                            data.append(dict(row))
                
                if self.config.cache_enabled:
                    # Delší TTL pro Open Data (aktualizace měsíčně)
                    await self._cache.set(cache_key, data, ttl=86400)  # 24h
                
                return data
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to download {dataset_name}: {e}")
            raise
    
    async def get_dlp_medicines(self) -> list[dict]:
        """Získej všechny léčivé přípravky z DLP."""
        return await self.download_csv_dataset("dlp", "dlp_lecivepripravky.csv")
    
    async def get_dlp_substances(self) -> list[dict]:
        """Získej účinné látky z DLP."""
        return await self.download_csv_dataset("dlp", "dlp_ucinnelatky.csv")
    
    async def get_pharmacies_from_opendata(self) -> list[dict]:
        """Získej seznam lékáren z Open Data."""
        return await self.download_csv_dataset("lekarny")
    
    # === Utility metody ===
    
    async def health_check(self) -> dict:
        """Zkontroluj dostupnost API."""
        results = {
            "api_available": False,
            "opendata_available": False,
            "cache_stats": self._cache.stats(),
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Test REST API
            await self._api_request("GET", "/info", use_cache=False)
            results["api_available"] = True
        except Exception as e:
            results["api_error"] = str(e)
        
        try:
            # Test Open Data
            response = await self.client.head(self.config.opendata_base_url)
            results["opendata_available"] = response.status_code == 200
        except Exception as e:
            results["opendata_error"] = str(e)
        
        return results
    
    async def clear_cache(self):
        """Vymaž cache."""
        await self._cache.clear()
        logger.info("Cache cleared")


# Dependency injection helper pro FastMCP
_client_instance: Optional[SUKLClient] = None


async def get_sukl_client() -> SUKLClient:
    """Získej sdílenou instanci klienta."""
    global _client_instance
    if _client_instance is None:
        _client_instance = SUKLClient()
        await _client_instance.connect()
    return _client_instance


async def close_sukl_client():
    """Uzavři sdílenou instanci."""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None
