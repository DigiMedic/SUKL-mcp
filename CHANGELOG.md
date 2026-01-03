# Changelog

All notable changes to SÚKL MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.0.0] - 2026-01-03

### Added - REST API Layer (Major Architecture Change)

#### New API Module (`src/sukl_mcp/api/`)
- **`SUKLAPIClient`** - Production-ready REST API client:
  - Async context manager pattern (`async with SUKLAPIClient()`)
  - Automatic retry with exponential backoff (3 attempts, configurable delay)
  - In-memory LRU cache with TTL (300s default, configurable)
  - Rate limiting with sliding window (60 req/min default)
  - Batch fetch with semaphore control (`get_medicines_batch()`)
  - Health check endpoint with latency measurement
  - Structured logging with operation metadata
- **Pydantic v2 Models** (`api/models.py`):
  - `APILecivyPripravek` - Medicine detail from `/dlp/v1/lecive-pripravky/{kod}`
  - `APISearchResponse` - Search results from `/dlp/v1/lecive-pripravky?nazev=...`
  - `APIHealthResponse` - Health check response
  - Full type safety with runtime validation
- **Configuration** (`api/client.py`):
  - `SUKLAPIConfig` - Dataclass with sensible defaults
  - Environment variable support (`SUKL_API_BASE_URL`, `SUKL_API_TIMEOUT`, etc.)
  - `CacheEntry` - TTL-aware cache with timestamp validation

#### Hybrid Search Architecture
- **Dual-client initialization** (`server.py:56-81`):
  - Primary: REST API client (real-time data from prehledy.sukl.cz)
  - Fallback: CSV client (local cache, 68k records in-memory)
  - Health checks for both clients on startup
  - Graceful degradation strategy
- **Helper function** `_try_rest_search()` (`server.py:173-232`):
  - Attempts REST API search first
  - Returns `(results, "rest_api")` on success
  - Returns `None` on failure (triggers CSV fallback)
  - Batch fetch with concurrent limit (5 parallel requests)
  - Data transformation: `APILecivyPripravek` → dict → Pydantic models
- **Updated `search_medicine` tool** (`server.py:235-333`):
  - Try REST API first (via `_try_rest_search()`)
  - Automatic CSV fallback on API errors
  - Match type prefix: `rest_api` or `csv_{match_type}`
  - Zero breaking changes - same API signature
  - Backward compatible with existing clients

#### Testing & Quality
- **22 unit tests** (`tests/test_api_client.py`):
  - Config validation (2 tests)
  - Cache mechanics (3 tests)
  - Search operations (3 tests)
  - Get medicine details (3 tests)
  - Rate limiting (1 test)
  - Health checks (2 tests)
  - Error handling (5 tests)
  - Batch operations (3 tests)
- **4 integration tests** against live SÚKL API:
  - Real search: "PARALEN" query (5 results)
  - Real detail: medicine "0254045"
  - Real health check (<100ms latency)
  - Real batch fetch (10 medicines)
- **100% pass rate** - All 241 tests passing (219 existing + 22 new)

#### Development Tools
- **Makefile targets**:
  - `make api-test` - Run integration tests against real API
  - `make api-health` - Quick API availability check
  - `make dev` - Full development workflow (format + test + lint)
- **Documentation updates**:
  - `docs/Phase-01-REST-API-Migration-Plan.md` - Implementation plan
  - `PRODUCT_SPECIFICATION.md` - Updated with v4.0 status
  - `CLAUDE.md` - REST API architecture and patterns

### Changed

#### Architecture
- **Primary data source**: REST API (prehledy.sukl.cz/dlp/v1) replacing CSV downloads
- **Hybrid mode**: REST API with CSV fallback for resilience
- **Server lifecycle**: Dual-client initialization in `server_lifespan()`
- **App context**: `AppContext` dataclass with typed `api_client` and `client` fields

#### Dependencies
- Added `httpx>=0.25.0` - Async HTTP client for REST API
- Added `tenacity>=8.0.0` - Retry logic with exponential backoff
- Updated `pydantic>=2.0.0` - Full Pydantic v2 migration

#### Performance
- **REST API latency**: ~97ms health check, ~100-160ms search (measured live)
- **CSV fallback**: ~50-150ms (in-memory pandas operations)
- **Cache hit rate**: TBD (monitoring needed)
- **No regression**: Existing tools maintain <200ms p95 latency

### Fixed
- Pydantic v2 deprecation warnings (`class Config` → `model_config`)
- All linting issues in new `api/` module (ruff + mypy clean)
- Type hints for all public API methods (mypy strict mode)

### Deprecated
- **`src/sukl_mcp/client_csv.py`** - Legacy CSV client
  - Status: Functional but deprecated
  - Removal: Planned for v5.0.0
  - Migration path: Switch to `SUKLAPIClient` for real-time data
- **Pandas dependency** - Will become optional in v5.0 (CSV export tool only)

### Migration Guide

#### For MCP Tool Users
No changes required - hybrid mode ensures backward compatibility.

#### For Developers
```python
# Old (v3.x) - CSV-based
from sukl_mcp.client_csv import get_sukl_client

client = await get_sukl_client()
results = await client.search_by_name("PARALEN", limit=10)

# New (v4.x) - REST API
from sukl_mcp.api import SUKLAPIClient

async with SUKLAPIClient() as client:
    # Search (returns codes)
    search_result = await client.search_medicines("PARALEN", limit=10)

    # Batch fetch details
    medicines = await client.get_medicines_batch(search_result.codes)

    # Single medicine detail
    medicine = await client.get_medicine("0254045")

    # Health check
    health = await client.health_check()
```

#### Configuration
```python
from sukl_mcp.api import SUKLAPIClient, SUKLAPIConfig

# Custom config
config = SUKLAPIConfig(
    base_url="https://prehledy.sukl.cz",  # Default
    timeout=30.0,                          # Request timeout
    max_retries=3,                         # Retry attempts
    cache_ttl=300,                         # Cache TTL in seconds
    rate_limit=60,                         # Max requests per minute
)

async with SUKLAPIClient(config) as client:
    # Use client...
```

### Performance Metrics

| Operation | REST API | CSV Fallback | Target |
|-----------|----------|--------------|--------|
| Health check | ~97ms | N/A | <100ms ✅ |
| Search (10 results) | ~100-160ms | ~50-150ms | <300ms ✅ |
| Get detail | ~80-120ms | ~10-50ms | <200ms ✅ |
| Batch fetch (10) | ~300-500ms | N/A | <1000ms ✅ |

### Known Limitations
- REST API doesn't provide price data (dlp_cau.csv) - CSV fallback required for `get_reimbursement()`
- Cache is in-memory only (not persistent across restarts)
- Rate limiting is client-side only (no server coordination)

### Next Steps (v4.1.0+)
- [ ] Migrate `get_medicine_details()` to REST API
- [ ] Migrate `check_availability()` to REST API
- [ ] Add persistent cache layer (Redis/SQLite)
- [ ] Implement server-side rate limiting coordination
- [ ] Add Prometheus metrics for monitoring
- [ ] Deprecation warnings for pure CSV usage

## [3.1.0] - 2026-01-02

### Performance Improvements
- **Non-blocking Fuzzy Search**: Refactored `FuzzyMatcher` to run CPU-intensive `rapidfuzz` operations in a separate thread executor, preventing event loop blocking during heavy searches.
- **PyArrow Backend**: Switched Pandas `dtype_backend` to `pyarrow` for significantly reduced memory usage and faster data loading.
- **Cold Start Fix**: Implemented explicit data initialization during server startup (`server_lifespan`) to eliminate latency on the first request.

### Changed
- Updated `SUKLClient` and `SUKLDataLoader` to support asynchronous initialization and PyArrow types.
- Refactored unit tests to support async execution of fuzzy search operations.

## [3.0.0] - 2026-01-01

### Added (EPIC 4: Availability & Alternatives)
- **Inteligentní doporučení alternativních léků** při nedostupnosti přípravku
- **Multi-kriteriální ranking system** pro alternativy:
  - Léková forma: 40% váha
  - Síla přípravku: 30% váha
  - Cena: 20% váha
  - Název (podobnost): 10% váha
- **Automatické hledání alternativ** ve dvou fázích:
  1. Stejná účinná látka (přes dlp_slozeni)
  2. Fallback na stejnou ATC skupinu (3-znakový prefix)
- **Batch enrichment** alternativ s cenovými údaji a doplatky
- **Strength parsing** s regex pro různé formáty (mg, g, ml, iu, %)
- **Strength similarity** kalkulace s unit normalizací (G→MG konverze)
- **AvailabilityStatus enum** pro normalizaci stavů (available/unavailable/unknown)
- **AlternativeMedicine model** s relevance_score a match_reason
- **5 nových metod** v SUKLClient:
  - `_normalize_availability()` - normalizace DODAVKY hodnot
  - `_parse_strength()` - extrakce numerických hodnot a jednotek
  - `_calculate_strength_similarity()` - porovnání sil přípravků
  - `_rank_alternatives()` - multi-kriteriální ranking
  - `find_generic_alternatives()` - hlavní algoritmus

### Changed
- `check_availability()` tool rozšířen o nové parametry:
  - `include_alternatives: bool = True` - zapnutí/vypnutí hledání alternativ
  - `limit: int = 5` - max počet alternativ (max 10)
- `AvailabilityInfo` model rozšířen:
  - `alternatives: list[AlternativeMedicine]` - seznam nalezených alternativ
  - `alternatives_available: bool` - flag existence alternativ
  - `recommendation: Optional[str]` - user-friendly doporučení

### Tests
- Přidáno **49 nových testů** pro EPIC 4 (celkem 197 testů)
- Coverage oblastí:
  - Normalizace dostupnosti (15 testů)
  - Parsing a similarity síly přípravků (20 testů)
  - Ranking algoritmus (9 testů)
  - End-to-end alternativy (5 testů)
- **100% pass rate** (197/197 testů)

### Performance
- find_generic_alternatives: <200ms (včetně price enrichment)
- Batch enrichment pattern pro efektivní cenové dotazy

---

## [2.3.0] - 2024-12-31

### Added (EPIC 3: Price & Reimbursement)
- **Cenové údaje** z dlp_cau.csv (Cenové a úhradové údaje)
- **Kalkulace doplatku pacienta** (maximální cena - úhrada pojišťovny)
- **price_calculator.py modul** s funkcemi:
  - `get_price_data()` - získání cenových údajů s validitou
  - `calculate_patient_copay()` - výpočet doplatku
  - `has_reimbursement()` - kontrola úhrady
  - `get_reimbursement_amount()` - výše úhrady
- **Column mapping** pro různé varianty názvů sloupců
- **Numeric value conversion** s graceful handling (čárky, mezery)
- **Date parsing** pro různé formáty (DD.MM.YYYY, YYYY-MM-DD)
- **Validity filtering** podle reference_date
- **Obohacení search výsledků** o cenové údaje:
  - has_reimbursement flag v MedicineSearchResult
  - max_price v search výsledcích
  - patient_copay v search výsledcích

### Changed
- `MedicineSearchResult` model rozšířen o cenové atributy:
  - `has_reimbursement: Optional[bool]`
  - `max_price: Optional[float]`
  - `patient_copay: Optional[float]`
- `MedicineDetail` model rozšířen o úhradové informace:
  - `has_reimbursement`, `max_price`, `reimbursement_amount`, `patient_copay`

### Tests
- Přidáno **44 testů** pro EPIC 3 (celkem 148 testů)
- Coverage: column mapping, numeric conversion, date parsing, price data extraction

---

## [2.1.0] - 2024-12-30

### Added (EPIC 2: Smart Search)
- **Multi-level search pipeline** pro komplexní vyhledávání:
  1. Vyhledávání podle účinné látky (dlp_slozeni)
  2. Exact match v názvu přípravku
  3. Substring match v názvu
  4. Fuzzy fallback (rapidfuzz, threshold 80)
- **fuzzy_search.py modul** s funkcemi:
  - `search_by_name_fuzzy()` - fuzzy vyhledávání s rapidfuzz
  - `_search_by_substance()` - hledání podle účinné látky
  - `_search_by_name_exact()` - exact match
  - `_search_by_name_substring()` - substring match
- **Smart scoring system** pro relevanci výsledků:
  - Dostupnost: +10 bodů
  - Úhrada pojišťovny: +5 bodů
  - Match type bonus: exact (+20), substance (+15), substring (+10), fuzzy (0-10)
- **Deduplication** výsledků s keep='first' strategií
- **Match metadata** v MedicineSearchResult:
  - `match_score: Optional[float]` - relevance skóre (0-100)
  - `match_type: Optional[str]` - typ matchování (substance/exact/substring/fuzzy)

### Changed
- `search_medicines()` tool rozšířen o `use_fuzzy: bool = True` parametr
- `MedicineSearchResult` model rozšířen o match metadata
- `SearchResponse` model rozšířen o `match_type` field

### Tests
- Přidáno **34 testů** pro EPIC 2 (celkem 104 testů)
- Coverage: pipeline stages, fuzzy matching, scoring, deduplication

---

## [2.0.0] - 2024-12-29

### Added (EPIC 1: Content Extractor)
- **Automatické parsování dokumentů** PDF a DOCX
- **document_parser.py modul** s třídami:
  - `DocumentDownloader` - stahování dokumentů s timeout a size limit
  - `PDFParser` - extrakce textu z PDF (PyMuPDF)
  - `DOCXParser` - extrakce textu z DOCX (python-docx)
  - `DocumentParser` - unified interface s LRU cache
- **LRU cache** pro parsované dokumenty (50 docs, 24h TTL)
- **Security features**:
  - Size limit: 10 MB pro PDF, 5 MB pro DOCX
  - Page limit: 100 stran pro PDF
  - Timeout: 30s download, 10s parsing
- **Content-Type detection** s fallback na URL extension
- **Graceful error handling** s fallback na URL při parse errors
- **PIL a SPC dokumenty** automaticky extrahovány z dlp_nazvydokumentu

### Changed
- `get_pil_document()` tool nyní vrací `full_text` místo pouze URL
- `PILContent` model rozšířen:
  - `full_text: Optional[str]` - extrahovaný text
  - `document_format: Optional[str]` - formát (pdf/docx)

### Dependencies
- Přidáno: PyMuPDF (fitz), python-docx, cachetools
- Vše async-compatible s httpx

### Tests
- Přidáno **47 testů** pro EPIC 1 (celkem 70 testů)
- Coverage: download, parsing, caching, error handling

---

## [1.0.0] - 2024-12-20

### Added
- **Initial release** SÚKL MCP Server
- **7 MCP tools** pro farmaceutická data:
  1. `search_medicines` - vyhledávání léčivých přípravků
  2. `get_medicine_detail` - detaily konkrétního přípravku
  3. `get_pil_document` - příbalové informace (PIL)
  4. `check_availability` - dostupnost léků
  5. `get_reimbursement_info` - informace o úhradách
  6. `search_pharmacies` - vyhledávání lékáren
  7. `get_atc_groups` - ATC klasifikace
- **SUKLClient** pro in-memory vyhledávání v pandas DataFrames
- **SUKLDataLoader** pro async stahování a extrakci SÚKL Open Data
- **Input validation** všech parametrů (query, SÚKL kód, limit, ATC prefix)
- **Security features**:
  - ZIP bomb protection (max 5 GB)
  - Regex injection prevention (regex=False)
  - Input sanitization
- **Thread-safe singleton** s double-checked locking
- **Async I/O** pro non-blocking operations
- **Pydantic modely** pro type-safe responses
- **Environment configuration** (cache dir, data dir, timeout, log level)
- **Dual deployment support**: stdio (FastMCP Cloud) + HTTP (Smithery)

### Data
- **68,248** registrovaných léčivých přípravků
- **787,877** záznamů složení (účinné látky)
- **3,352** různých léčivých látek
- **6,907** ATC klasifikačních kódů
- **61,240** dokumentů (PIL, SPC)

### Tests
- **23 testů** pro core functionality
- Coverage: validation, async I/O, race conditions, security

### Documentation
- README.md s Quick Start guide
- CLAUDE.md s development instructions
- docs/ adresář s 8 MD soubory (125+ stránek)

---

## Links

- [GitHub Repository](https://github.com/your-org/fastmcp-boilerplate)
- [SÚKL Open Data](https://opendata.sukl.cz)
- [FastMCP Framework](https://gofastmcp.com)
- [Model Context Protocol](https://modelcontextprotocol.io)
