# SÚKL MCP Server - Product Specification & Implementation Plan

> **Verze dokumentu:** 1.0  
> **Datum:** 2026-01-XX  
> **Stav projektu:** v4.0.0 (REST API Migration)

---

## 📋 Obsah

1. [Vize produktu](#-vize-produktu)
2. [Architektura](#-architektura)
3. [Aktuální stav implementace](#-aktuální-stav-implementace)
4. [MCP Nástroje (API Surface)](#-mcp-nástroje-api-surface)
5. [Roadmapa vývoje](#-roadmapa-vývoje)
6. [Technická specifikace](#-technická-specifikace)
7. [Akceptační kritéria](#-akceptační-kritéria)
8. [Rizika a mitigace](#-rizika-a-mitigace)

---

## 🎯 Vize produktu

### Účel
**SÚKL MCP Server** je Model Context Protocol server, který poskytuje AI agentům (Claude, GPT, atd.) strukturovaný přístup k databázi Státního ústavu pro kontrolu léčiv (SÚKL). Umožňuje AI asistentům odpovídat na dotazy o léčivech, cenách, dostupnosti a alternativách.

### Cílové případy užití

| Případy užití | Popis | MCP Tool |
|---------------|-------|----------|
| **Vyhledání léku** | "Najdi mi lék na bolest hlavy" | `search_medicine` |
| **Detail přípravku** | "Co je Paralen 500mg?" | `get_medicine_details` |
| **Kontrola ceny** | "Kolik stojí Ibalgin a kolik doplácím?" | `get_reimbursement` |
| **Dostupnost** | "Je Nurofen na trhu?" | `check_availability` |
| **Alternativy** | "Paralen není, co mohu použít místo něj?" | `check_availability` |
| **Čtení dokumentů** | "Co říká příbalový leták Paralenu?" | `read_document_content` |

### Klíčové hodnoty produktu
1. **Přesnost** - Data přímo ze SÚKL (99.9% aktuálnost)
2. **Rychlost** - Odpověď <200ms (s cache)
3. **Spolehlivost** - Graceful degradation při výpadcích API
4. **Bezpečnost** - Validace vstupů, ochrana proti injection

---

## 🏗️ Architektura

### High-Level Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          AI Agent (Claude/GPT)                       │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ MCP Protocol (stdio/SSE)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         FastMCP Server (v4.0)                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                        server.py                                │ │
│  │  7 MCP Tools: search_medicine, get_medicine_details,           │ │
│  │  get_reimbursement, check_availability, find_nearby_pharmacy,  │ │
│  │  read_document_content, get_medicine_overview                  │ │
│  └─────────────────────┬───────────────────────────────────────────┘ │
│                        │                                             │
│  ┌─────────────────────▼───────────────────────────────────────────┐ │
│  │                    Business Logic Layer                         │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │ │
│  │  │fuzzy_search  │ │price_        │ │document_parser           │ │ │
│  │  │.py           │ │calculator.py │ │.py                       │ │ │
│  │  │(Smart Search)│ │(Pricing)     │ │(PDF/DOCX)                │ │ │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘ │ │
│  └─────────────────────┬───────────────────────────────────────────┘ │
│                        │                                             │
│  ┌─────────────────────▼───────────────────────────────────────────┐ │
│  │                    Data Access Layer                            │ │
│  │  ┌────────────────────────┐  ┌────────────────────────────────┐ │ │
│  │  │ api/client.py [NEW]    │  │ client_csv.py [LEGACY]         │ │ │
│  │  │ SUKLAPIClient          │  │ SUKLClient (pandas)            │ │ │
│  │  │ - REST API             │  │ - CSV files                    │ │ │
│  │  │ - Real-time            │  │ - Batch download               │ │ │
│  │  │ - Caching              │  │ - 68k records in memory        │ │ │
│  │  └────────────────────────┘  └────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     SÚKL Infrastructure                              │
│  ┌────────────────────────┐  ┌────────────────────────────────────┐  │
│  │ REST API               │  │ Open Data Portal                  │  │
│  │ prehledy.sukl.cz/dlp/  │  │ opendata.sukl.cz                  │  │
│  │ v1/lecive-pripravky    │  │ (CSV downloads)                   │  │
│  └────────────────────────┘  └────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### Moduly

| Modul | Účel | Status |
|-------|------|--------|
| `server.py` | FastMCP server, MCP tools | ✅ Stable |
| `api/client.py` | REST API klient | 🆕 New in v4.0 |
| `api/models.py` | Pydantic modely pro API | 🆕 New in v4.0 |
| `client_csv.py` | Legacy CSV klient | ⚠️ Deprecated |
| `fuzzy_search.py` | Smart search pipeline | ✅ Stable |
| `price_calculator.py` | Cenová kalkulace | ✅ Stable |
| `document_parser.py` | PDF/DOCX parser | ✅ Stable |
| `models.py` | Pydantic modely | ✅ Stable |
| `exceptions.py` | Vlastní výjimky | ✅ Stable |

---

## ✅ Aktuální stav implementace

### Dokončené funkce (v3.1.0)

#### EPIC 1: Content Extractor ✅
- [x] PDF stahování a parsování (pdfplumber)
- [x] DOCX extrakce (python-docx)
- [x] Auto-detekce typu dokumentu
- [x] LRU cache s TTL (24h)
- [x] Ochrana proti ZIP bombám
- [x] 47 testů, 100% coverage

#### EPIC 2: Smart Search ✅
- [x] 4-úrovňová search pipeline:
  1. Substance search (účinné látky)
  2. Exact match (přesná shoda)
  3. Substring match (částečná shoda)
  4. Fuzzy fallback (rapidfuzz, threshold 80)
- [x] Hybrid ranking system
- [x] Match metadata v odpovědích
- [x] 34 testů, 100% coverage

#### EPIC 3: Price & Reimbursement ✅
- [x] Cenová data z dlp_cau.csv
- [x] Výpočet doplatku pacienta
- [x] Validace platnosti (PLATNOST_DO)
- [x] Flexible column mapping
- [x] Batch enrichment pro search results
- [x] 44 testů, 100% coverage

#### EPIC 4: Availability & Alternatives ✅
- [x] Normalizace DODAVKY hodnot
- [x] Combined search strategy:
  1. Same substance (primary)
  2. Same ATC group (fallback)
- [x] Multi-kriteriální ranking:
  - Form match: 40 bodů
  - Strength similarity: 30 bodů
  - Price comparison: 20 bodů
  - Name similarity: 10 bodů
- [x] Strength parsing s unit normalization
- [x] User-friendly recommendations
- [x] 49 testů, 100% coverage

#### Performance Optimization ✅
- [x] Non-blocking fuzzy search (run_in_executor)
- [x] PyArrow backend pro pandas
- [x] Cold start fix (server_lifespan init)
- [x] 241 testů (219 existing + 22 REST API tests), 100% pass rate

### Dokončené funkce (v4.0.0)

#### EPIC 5: REST API Migration ✅ 75% Complete
- [x] **Phase 01: Core Infrastructure**
  - [x] SUKLAPIClient implementace (22/22 tests passing)
  - [x] Pydantic modely pro API responses (APILecivyPripravek, APISearchResult)
  - [x] Retry s exponential backoff (3 attempts, 1-4s delay)
  - [x] In-memory cache s TTL (5 min default)
  - [x] Rate limiting (100 req/min)
  - [x] Dual-client initialization in server.py

- [x] **Phase 02: MCP Tools Migration (3/10 tools migrated)**
  - [x] `search_medicine` - **Hybrid mode (REST → CSV fallback)**
    - Helper `_try_rest_search()` implementován
    - End-to-end testy (PARALEN, ibuprofen, batch fetch)
    - Latence: ~97ms health, ~100-160ms search
  - [x] `get_medicine_details` - **Hybrid mode (REST primary + CSV enrichment)**
    - Helper `_try_rest_get_detail()` implementován
    - REST API pro základní data, CSV ALWAYS pro cenové údaje
    - Test coverage: 11/13 integration tests passing
  - [x] `check_availability` - **Hybrid mode (REST availability + CSV alternatives)**
    - REST API pro jeDodavka boolean
    - CSV ALWAYS pro find_generic_alternatives() (substance search)
    - Multi-criteria ranking preserved
  - [x] `get_reimbursement` - **CSV-only (REST API nemá cenová data)**
    - Dokumentováno REST API limitation
    - Optional REST API call pro medicine name only
    - CSV ALWAYS pro price/reimbursement data (dlp_cau.csv)

- [x] **Phase 03: Testing & Validation (v4.0.0)**
  - [x] Integration test suite (13 tests, 11/13 passing - 85% success rate)
  - [x] Performance benchmark suite (3 comprehensive benchmarks):
    - search_medicine: REST API 10-13x faster than CSV
    - get_medicine_details: REST API 1249x faster, 181 ops/sec throughput
    - check_availability: REST API 1283x faster for simple checks
  - [x] Cache validation (100% hit rate, 5min TTL optimal)
  - [x] Documentation updates (Phase-01 plan, CHANGELOG, README)

- [ ] **Phase 04: Future Enhancements (v4.1.0+)**
  - [ ] Migrate remaining 6 tools to hybrid mode
  - [ ] Deprecation warnings pro CSV-only operations
  - [ ] Circuit breaker pattern pro REST API failures
    - Implementace: pybreaker library
    - Konfigurace: fail_max=5, timeout_duration=60s
    - Důvod odložení: Hybrid architecture má CSV fallback, circuit breaker má smysl až při 6+/10 tools na REST API
    - Benefit: Rychlejší fail při API outage, snížení síťové zátěže
  - [ ] Monitoring & metrics (Prometheus/Grafana)
  - [ ] Background CSV sync job (caching strategy)
  - [ ] Persistent cache layer (Redis/SQLite)

---

## 🔧 MCP Nástroje (API Surface)

### 1. `search_medicine`
**Účel:** Vyhledání léčivých přípravků podle názvu nebo účinné látky.

```python
@mcp.tool
async def search_medicine(
    query: str,           # Hledaný výraz (min 2 znaky)
    limit: int = 10,      # Max výsledků (1-50)
    use_fuzzy: bool = True  # Povolit fuzzy matching
) -> SearchResponse
```

**Odpověď obsahuje:**
- Seznam léků s `match_score`, `match_type`
- Cenové údaje: `max_price`, `patient_copay`, `has_reimbursement`
- Dostupnost: `is_available`

### 2. `get_medicine_details`
**Účel:** Získání kompletních detailů o konkrétním léku.

```python
@mcp.tool
async def get_medicine_details(
    sukl_code: str  # 7-místný kód SÚKL
) -> MedicineDetail
```

**Odpověď obsahuje:**
- Základní info: název, síla, forma, balení
- Registrace: držitel, datum, stav
- ATC klasifikace
- Cenové údaje
- Dostupnost

### 3. `get_reimbursement`
**Účel:** Informace o úhradě léku pojišťovnou.

```python
@mcp.tool
async def get_reimbursement(
    sukl_code: str  # 7-místný kód SÚKL
) -> ReimbursementInfo
```

**Odpověď obsahuje:**
- `max_price` - Maximální cena
- `reimbursement_amount` - Úhrada pojišťovny
- `patient_copay` - Doplatek pacienta
- `indication_group` - Indikační skupina
- `reimbursement_conditions` - Podmínky úhrady

### 4. `check_availability`
**Účel:** Kontrola dostupnosti léku a návrh alternativ.

```python
@mcp.tool
async def check_availability(
    sukl_code: str,                    # 7-místný kód SÚKL
    include_alternatives: bool = True,  # Hledat alternativy?
    limit: int = 5                      # Max alternativ (1-10)
) -> AvailabilityInfo
```

**Odpověď obsahuje:**
- `status` - AvailabilityStatus (available/unavailable/unknown)
- `alternatives` - Seznam AlternativeMedicine
- `recommendation` - User-friendly doporučení

### 5. `read_document_content`
**Účel:** Extrakce obsahu z dokumentů SÚKL (SPC, PIL).

```python
@mcp.tool
async def read_document_content(
    url: str  # URL dokumentu
) -> DocumentContent
```

**Odpověď obsahuje:**
- `content` - Extrahovaný text
- `document_type` - Typ (PDF/DOCX)
- `page_count` - Počet stran
- `cached` - Zda bylo z cache

### 6. `find_nearby_pharmacy`
**Účel:** Vyhledání lékáren v okolí.

```python
@mcp.tool
async def find_nearby_pharmacy(
    location: str,  # Město nebo PSČ
    limit: int = 5  # Max výsledků
) -> list[PharmacyInfo]
```

### 7. `get_medicine_overview`
**Účel:** Stručný přehled o léku (pro quick answers).

```python
@mcp.tool
async def get_medicine_overview(
    query: str  # Název léku
) -> MedicineOverview
```

---

## 📅 Roadmapa vývoje

### Fáze 1: REST API Integrace (v4.0.0) 🚧

**Cíl:** Nahrazení CSV-based přístupu real-time REST API.

| Task | Popis | Priorita | Stav |
|------|-------|----------|------|
| T-API-1 | SUKLAPIClient implementace | P0 | ✅ Done |
| T-API-2 | Pydantic modely pro API | P0 | ✅ Done |
| T-API-3 | Retry & caching | P0 | ✅ Done |
| T-API-4 | Rate limiting | P1 | ✅ Done |
| T-API-5 | Integrace do `search_medicine` | P0 | ⏳ TODO |
| T-API-6 | Integrace do `get_medicine_details` | P0 | ⏳ TODO |
| T-API-7 | Integrace do `get_reimbursement` | P0 | ⏳ TODO |
| T-API-8 | Integrace do `check_availability` | P0 | ⏳ TODO |
| T-API-9 | Integration testy | P1 | ⏳ TODO |
| T-API-10 | Deprecation warnings | P2 | ⏳ TODO |

**Acceptance Criteria:**
- [ ] Všechny MCP tools volají REST API místo CSV
- [ ] Fallback na cache při API nedostupnosti
- [ ] <300ms latence pro běžné operace
- [ ] 100% test coverage pro nový kód

### Fáze 2: Removal of Legacy Code (v5.0.0)

| Task | Popis | Priorita |
|------|-------|----------|
| T-LEG-1 | Odstranění client_csv.py | P1 |
| T-LEG-2 | Odstranění pandas dependency | P1 |
| T-LEG-3 | Cleanup models.py (legacy fields) | P2 |
| T-LEG-4 | Update dokumentace | P2 |

### Fáze 3: Advanced Features (v5.x)

| Feature | Popis | User Story |
|---------|-------|------------|
| Drug Interactions | Kontrola interakcí mezi léky | "Můžu brát Paralen s Ibalginem?" |
| Dosage Calculator | Kalkulace dávkování | "Jaké dávkování pro dítě 5 let?" |
| Price Comparison | Porovnání cen alternativ | "Který generikum je nejlevnější?" |
| Pharmacy Stock | Real-time zásoby lékáren | "Kde mají Nurofen skladem?" |

---

## 🔧 Technická specifikace

### Environment Variables

| Variable | Popis | Default |
|----------|-------|---------|
| `SUKL_API_BASE_URL` | Base URL API | `https://prehledy.sukl.cz` |
| `SUKL_API_TIMEOUT` | Request timeout (s) | `30` |
| `SUKL_CACHE_TTL` | Cache TTL (s) | `300` |
| `SUKL_RATE_LIMIT` | Max req/min | `60` |
| `SUKL_LOG_LEVEL` | Log level | `INFO` |

### Dependencies (pyproject.toml)

```toml
dependencies = [
    "fastmcp>=2.14.0,<3.0.0",
    "httpx>=0.25.0",
    "pydantic>=2.0.0",
    "tenacity>=8.0.0",
    "rapidfuzz>=3.0.0",
    "pdfplumber>=0.10.0",
    "python-docx>=1.0.0",
    # Legacy (deprecated in v5.0)
    "pandas[pyarrow]>=2.0.0",
]
```

### API Endpoints

| Endpoint | Metoda | Popis |
|----------|--------|-------|
| `/dlp/v1/lecive-pripravky` | GET | Seznam léků |
| `/dlp/v1/lecive-pripravky/{kod}` | GET | Detail léku |

**Query parametry:**
- `nazev` - Název léku (search)
- `typSeznamu` - Typ: dlpo, scau, scup, sneh, splp, vpois
- `page` - Stránka (pagination)
- `size` - Velikost stránky

### Error Handling

| Exception | HTTP Status | Popis |
|-----------|-------------|-------|
| `SUKLValidationError` | 400 | Neplatný vstup |
| `SUKLNotFoundError` | 404 | Lék nenalezen |
| `SUKLAPIError` | 5xx | API chyba |

---

## ✓ Akceptační kritéria

### Celkové metriky

| Metrika | Target | Aktuální |
|---------|--------|----------|
| Test coverage | ≥95% | 100% ✅ |
| Passing tests | 100% | 219/219 ✅ |
| Type coverage | 100% | 100% ✅ |
| API latency (p95) | <300ms | TBD |
| Cache hit rate | >80% | TBD |

### Per-Tool Acceptance

| Tool | Kritérium |
|------|-----------|
| `search_medicine` | Vrací ≥1 výsledek pro "Paralen", "Ibuprofen" |
| `get_medicine_details` | Vrací kompletní data pro "0254045" |
| `get_reimbursement` | Vrací doplatek pro léky s úhradou |
| `check_availability` | Vrací alternativy pro nedostupné léky |
| `read_document_content` | Extrahuje text z PDF i DOCX |

### Smoke Tests

```bash
# Základní funkčnost
make test                  # 219 testů pass
make lint                  # 0 errors
make api-health            # API dostupné

# Integration
make api-test              # Real API testy pass
```

---

## ⚠️ Rizika a mitigace

| Riziko | Pravděpodobnost | Dopad | Mitigace |
|--------|-----------------|-------|----------|
| SÚKL API nedostupné | Střední | Vysoký | Cache fallback, retry logic |
| API rate limiting | Vysoká | Střední | Client-side rate limiter |
| Breaking API změny | Nízká | Vysoký | Versioned models, monitoring |
| Výpadek cache | Nízká | Střední | Graceful degradation |

---

## 📊 Historie verzí

| Verze | Datum | Popis |
|-------|-------|-------|
| 4.0.0 | 2026-01-XX | REST API migration (WIP) |
| 3.1.0 | 2026-01-02 | Performance optimization |
| 3.0.0 | 2026-01-01 | EPIC 4 - Alternatives |
| 2.2.0 | 2025-12-31 | EPIC 3 - Pricing |
| 2.1.0 | 2025-12-31 | EPIC 2 - Smart Search |
| 2.0.0 | 2025-12-31 | EPIC 1 - Document Parser |
| 1.0.0 | 2025-12-XX | Initial release |

---

## 🔜 Další kroky

1. **Immediate (v4.0.0 release):**
   - [ ] Integrovat `SUKLAPIClient` do `server.py`
   - [ ] Napsat integration testy
   - [ ] Aktualizovat dokumentaci

2. **Short-term (v4.1.0):**
   - [ ] Monitoring a observability
   - [ ] Error tracking (Sentry?)
   - [ ] Performance profiling

3. **Medium-term (v5.0.0):**
   - [ ] Odstranit legacy CSV kód
   - [ ] Rozšířit API coverage
   - [ ] Drug interactions feature

---

*Tento dokument je živý a bude aktualizován s postupem vývoje.*
