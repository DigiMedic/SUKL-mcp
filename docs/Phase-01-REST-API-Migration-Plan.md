# Phase 01: REST API Migration - Implementační plán

**Status:** ✅ 75% DOKONČENO (3/4 tools migrated)
**Datum zahájení:** 2026-01-03
**Datum aktualizace:** 2026-01-03
**Odpovědná osoba:** Development Team

**Migrated Tools:**
- ✅ `search_medicine` - Hybrid mode (REST → CSV fallback)
- ✅ `get_medicine_details` - Hybrid mode (REST + CSV enrichment)
- ✅ `check_availability` - Hybrid mode (REST availability + CSV alternatives)
- 📄 `get_reimbursement` - CSV-only (REST API limitation documented)

## ✅ Dokončené kroky

### 1. REST API Klient implementace
- [x] `SUKLAPIClient` s async context manager
- [x] Pydantic modely (`APILecivyPripravek`, `APISearchResponse`, atd.)
- [x] Retry s exponential backoff (3 pokusy)
- [x] In-memory cache s TTL (5 minut)
- [x] Rate limiting (60 req/min)
- [x] Health check endpoint
- [x] Batch fetch s semaphore limitem

### 2. Testování
- [x] **22 unit testů** - 100% pass rate
  - Config tests (2)
  - Cache tests (3)
  - Search tests (3)
  - Get medicine tests (3)
  - Rate limiting tests (1)
  - Health check tests (2)
- [x] **4 integration testy** proti živému SÚKL API
  - Real search
  - Real get medicine
  - Real health check
  - Real batch fetch
- [x] Živé volání ověřeno: search, detail, batch, cache

### 3. Server integrace
- [x] Import SUKLAPIClient do server.py
- [x] Rozšíření AppContext o `api_client`
- [x] Dual-client initialization v `server_lifespan`
- [x] Export `get_api_client()` a `close_api_client()`
- [x] Verifikace startu serveru s dual-mode

## ✅ Aktuální milestone: Hybrid Search COMPLETED

### Strategie: Try REST → Fallback to CSV (IMPLEMENTOVÁNO)

```python
async def search_medicine_hybrid(query: str, limit: int = 20):
    """
    Hybrid search strategy:
    1. TRY: REST API (fast, real-time)
    2. CATCH: SUKLAPIError → fallback to CSV
    3. Log which mode was used
    """
    api_client = await get_api_client()
    csv_client = await get_sukl_client()

    try:
        # PRIMARY: REST API
        result = await api_client.search_medicines(query, limit=limit)
        codes = result.codes

        # Batch fetch details
        medicines = await api_client.get_medicines_batch(codes)
        logger.info(f"✅ REST API: {len(medicines)} results")
        return medicines, "rest_api"

    except SUKLAPIError as e:
        # FALLBACK: CSV
        logger.warning(f"⚠️  REST API failed: {e}, falling back to CSV")
        results, match_type = await csv_client.search_medicines(query, limit)
        logger.info(f"✅ CSV fallback: {len(results)} results")
        return results, f"csv_fallback_{match_type}"
```

### Implementační kroky

#### Krok 1: Helper funkce pro hybrid mode
```python
# src/sukl_mcp/server.py

async def _try_rest_search(
    query: str,
    limit: int,
    typ_seznamu: str = "dlpo"
) -> tuple[list[dict], str] | None:
    """
    Pokusí se vyhledat přes REST API.

    Returns:
        tuple[list[dict], str]: (results, "rest_api") nebo None při chybě
    """
    try:
        api_client = await get_api_client()

        # Search pro získání kódů
        search_result = await api_client.search_medicines(
            query=query,
            typ_seznamu=typ_seznamu,
            limit=limit
        )

        if not search_result.codes:
            logger.info(f"REST API: žádné výsledky pro '{query}'")
            return [], "rest_api"

        # Batch fetch details
        medicines = await api_client.get_medicines_batch(
            search_result.codes[:limit],
            max_concurrent=5
        )

        # Convert APILecivyPripravek -> dict pro kompatibilitu
        results = []
        for med in medicines:
            results.append({
                "kod_sukl": med.kodSUKL,
                "nazev": med.nazev,
                "sila": med.sila,
                "forma": med.lekovaFormaKod,
                "baleni": med.baleni,
                "atc": med.ATCkod,
                "stav_registrace": med.stavRegistraceKod,
                "vydej": med.zpusobVydejeKod,
                "dostupnost": "ano" if med.jeDodavka else "ne",
                # Match metadata
                "match_score": 20.0,  # Exact match from API
                "match_type": "exact",
            })

        logger.info(f"✅ REST API: {len(results)}/{len(search_result.codes)} results")
        return results, "rest_api"

    except (SUKLAPIError, Exception) as e:
        logger.warning(f"⚠️  REST API search failed: {e}")
        return None
```

#### Krok 2: Refactor search_medicine
```python
@mcp.tool
async def search_medicine(
    query: str,
    only_available: bool = False,
    only_reimbursed: bool = False,
    limit: int = 20,
    use_fuzzy: bool = True,
) -> SearchResponse:
    """
    Vyhledá léčivé přípravky (REST API + CSV fallback).

    v4.0: Hybrid mode - zkusí REST API, při selhání fallback na CSV.
    """
    start_time = datetime.now()

    # TRY: REST API (primary)
    rest_result = await _try_rest_search(query, limit)

    if rest_result is not None:
        raw_results, match_type = rest_result
    else:
        # FALLBACK: CSV client
        logger.info(f"🔄 Falling back to CSV for query: '{query}'")
        csv_client = await get_sukl_client()
        raw_results, match_type = await csv_client.search_medicines(
            query=query,
            limit=limit,
            only_available=only_available,
            only_reimbursed=only_reimbursed,
            use_fuzzy=use_fuzzy,
        )
        match_type = f"csv_{match_type}"

    # Rest of the function stays the same...
    # (transform to Pydantic models, etc.)
```

### 4. Hybrid Search Implementation ✅

**Krok 3: Helper funkce `_try_rest_search()`** (server.py:173-232)
```python
async def _try_rest_search(
    query: str, limit: int, typ_seznamu: str = "dlpo"
) -> tuple[list[dict], str] | None:
    """Pokusí se vyhledat přes REST API."""
    try:
        api_client = await get_api_client()
        search_result = await api_client.search_medicines(query, typ_seznamu, limit)
        medicines = await api_client.get_medicines_batch(search_result.codes[:limit])

        # Convert APILecivyPripravek -> dict pro kompatibilitu
        results = [{"kod_sukl": m.kodSUKL, "nazev": m.nazev, ...} for m in medicines]
        return results, "rest_api"
    except (SUKLAPIError, Exception) as e:
        logger.warning(f"REST API failed: {e}")
        return None
```

**Krok 4: Refaktor `search_medicine()` na hybrid** (server.py:235-318)
- Primární cesta: `_try_rest_search()`
- Fallback: CSV client při selhání REST API
- Zachována zpětná kompatibilita (stejný return type)
- Match type prefix: `rest_api` nebo `csv_{match_type}`

**Krok 5: End-to-end testování** (test_hybrid_search.py)
- ✅ REST API search: PARALEN (5 results)
- ✅ Limit respektován: ibuprofen (3 results)
- ✅ Batch fetch: 10 medicines s validními daty
- ✅ Latence: ~97ms health check, ~100-160ms search
- ✅ Data transformace: API → dict → Pydantic models

## ✅ Completed kroky (Phase 01 Extension)

- [x] **Krok 6:** Migrace `get_medicine_details()` ✅ HOTOVO
  - Helper `_try_rest_get_detail()` implementován
  - REST API primary pro základní data
  - CSV ALWAYS pro cenové údaje (dlp_cau.csv)
  - Zero breaking changes

- [x] **Krok 7:** Migrace `check_availability()` ✅ HOTOVO
  - REST API pro `jeDodavka` boolean (availability check)
  - CSV ALWAYS pro `find_generic_alternatives()` (substance search)
  - Multi-criteria ranking preserved

- [x] **Krok 8:** Dokumentace `get_reimbursement()` jako CSV-only ✅ HOTOVO
  - REST API **NEMÁ** cenová data (critical limitation)
  - dlp_cau.csv je jediný zdroj price/reimbursement info
  - Optional REST API call pro medicine name only
  - Extensive docstring s REST API limitations

- [x] **Krok 11:** Integration test suite pro hybrid mode ✅ 11/13 PASSED
  - `tests/test_hybrid_tools.py` (13 testů, 85% pass rate)
  - Core hybrid workflows verified: get_detail, check_availability, search
  - Data consistency REST vs CSV validated
  - CSV-only operations tested (pricing, alternatives)

## 📋 Pending kroky (v4.1.0)

- [ ] **Krok 9:** Update CLAUDE.md s REST API patterny
- [ ] **Krok 10:** Update docs/api-reference.md
- [ ] **Krok 12:** Performance benchmark (REST vs CSV)
- [ ] **Krok 13:** Deprecation warnings pro pure CSV usage

## 🎯 Success Criteria

- [ ] Všechny MCP tools fungují v hybrid mode
- [ ] Fallback na CSV při REST API nedostupnosti
- [ ] Latence REST API < 300ms (95th percentile)
- [ ] Cache hit rate > 60% po 1 hodině provozu
- [ ] Zero breaking changes pro existující uživatele
- [ ] Documentation aktualizována

## 📊 Metriky

- **REST API latence:** ~100-160ms (ověřeno živě)
- **CSV latence:** ~50-150ms (in-memory)
- **Cache hit rate:** TBD
- **Reliability:** TBD (monitoring needed)

## 🔗 Související dokumenty

- [PRODUCT_SPECIFICATION.md](../PRODUCT_SPECIFICATION.md) - Celková roadmapa
- [IMPLEMENTATION_BACKLOG.md](../IMPLEMENTATION_BACKLOG.md) - Historický backlog
- [docs/architecture.md](./architecture.md) - Architektonická dokumentace
