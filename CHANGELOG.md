# Changelog

All notable changes to SÚKL MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

- [GitHub Repository](https://github.com/DigiMedic/SUKL-mcp)
- [SÚKL Open Data](https://opendata.sukl.cz)
- [FastMCP Framework](https://gofastmcp.com)
- [Model Context Protocol](https://modelcontextprotocol.io)
