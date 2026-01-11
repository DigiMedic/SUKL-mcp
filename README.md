# SUKL MCP Server

**Production-ready FastMCP server** poskytující AI agentům přístup k oficiální české databázi léčivých přípravků SÚKL (Státní ústav pro kontrolu léčiv).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.14+-green.svg)](https://gofastmcp.com)
[![Version](https://img.shields.io/badge/version-5.0.2-brightgreen.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-264%20passed-success.svg)](tests/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **v5.0.2** - FastMCP 2.14+ compliance: 100% annotations coverage, modernizovaný Context pattern. [Changelog →](CHANGELOG.md)

---

## 📋 O projektu

SÚKL MCP Server je implementace [Model Context Protocol](https://modelcontextprotocol.io/) serveru, který umožňuje AI asistentům (jako Claude, GPT-4, atd.) přístup k aktuálním informacím o léčivých přípravcích registrovaných v České republice.

### Klíčové vlastnosti

- ✅ **Production-ready (v5.0.1)**: Opraveny kritické chyby, všechny nástroje správně registrovány
- 🎯 **Accurate match scoring**: 0-100 škála založená na rapidfuzz (ne hardcoded 20.0)
- 📊 **Complete data enrichment**: Cenová data přímo v search results (1 API call místo 2+)
- 🔍 **8 MCP tools** pro komplexní práci s farmaceutickými daty
- 🌐 **Hybrid Architecture (v4.0)**: REST API + CSV fallback pro 100% uptime
  - **3/10 tools migrované** na dual-mode (search, details, availability)
  - REST API primary (~100-160ms) → CSV fallback (~50ms)
  - Graceful degradation při API nedostupnosti
- 📄 **Automatické parsování dokumentů**: Extrakce textu z PIL/SPC (PDF + DOCX)
- 🎯 **Smart Search**: Multi-level pipeline s fuzzy matchingem (tolerance překlepů)
- 💰 **Cenové údaje**: Transparentní informace o úhradách a doplatcích pacientů
- 🔄 **Inteligentní alternativy**: Automatické doporučení náhradních léků při nedostupnosti (multi-kriteriální ranking)
- 💊 **68,248 léčivých přípravků** z SÚKL Open Data
- ⚡ **Async I/O** s pandas DataFrames pro rychlé vyhledávání
- 🔒 **Security features**: ZIP bomb protection, regex injection prevention
- 🏆 **Type-safe**: Pydantic v2 modely s runtime validací
- 🚀 **Dual deployment**: FastMCP Cloud (stdio) + Smithery (HTTP/Docker)
- ✅ **264 comprehensive tests** s pytest a coverage >85% (241 původních + 23 REST API testů)
- 🎯 **Full FastMCP 2.14+**: Context logging, Progress reporting, Resource templates, Tool annotations

### Datová základna

- **68,248** registrovaných léčivých přípravků
- **787,877** záznamů složení (účinné látky)
- **3,352** různých léčivých látek
- **6,907** ATC klasifikačních kódů
- **61,240** dokumentů (PIL - příbalové letáky, SPC - souhrny)

*Data aktualizována: 23. prosince 2024* (automatická měsíční aktualizace ze SÚKL Open Data)

---

## ⚡ Quick Start

### Instalace

```bash
# 1. Klonovat repozitář
git clone https://github.com/DigiMedic/SUKL-mcp.git
cd SUKL-mcp

# 2. Vytvořit virtuální prostředí
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 3. Instalovat projekt s dev závislostmi
pip install -e ".[dev]"
```

### Spuštění serveru

```bash
# Lokální vývoj (stdio transport)
python -m sukl_mcp

# Nebo pomocí Makefile
make run
```

### Konfigurace pro Claude Desktop

Přidej do `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sukl": {
      "command": "python",
      "args": ["-m", "sukl_mcp"],
      "env": {
        "PYTHONPATH": "/cesta/k/SUKL-mcp/src"
      }
    }
  }
}
```

Restart Claude Desktop a server bude k dispozici.

### Použití Production Serveru (Nejjednodušší)

Pro okamžité použití bez instalace, připoj se k produkčnímu serveru:

```bash
claude mcp add --scope local --transport http SUKL-mcp https://SUKL-mcp.fastmcp.app/mcp
```

Server se automaticky přidá do Claude Desktop konfigurace a je okamžitě k dispozici. Žádná instalace nebo lokální setup není potřeba!

**Chceš používat více MCP serverů současně?** Podívej se na [Multi-Server Setup Guide](docs/multi-server-setup.md) pro konfiguraci SÚKL serveru s dalšími službami (filesystem, GitHub, web search, atd.).

---

## 🛠️ MCP Tools

Server poskytuje **8 specializovaných nástrojů** pro práci s farmaceutickými daty (+ 5 MCP resources včetně 2 dynamických templates a 3 prompty):

> 💡 **FastMCP Best Practices**: Všechny nástroje používají `readOnlyHint` annotation pro přeskočení potvrzovacích dialogů, `Context` objekt pro client-side logging a `tags` pro kategorizaci.

### 1. `search_medicine` - Vyhledávání léčivých přípravků
**Smart Search** s multi-level pipeline a fuzzy matchingem pro toleranci překlepů.

**Pipeline:**
1. Vyhledávání v účinné látce (dlp_slozeni)
2. Exact match v názvu
3. Substring match v názvu
4. Fuzzy fallback (rapidfuzz, threshold 80)

**Scoring:** Dostupnost (+10), Úhrada (+5), Match type (exact: +20, substance: +15, substring: +10, fuzzy: 0-10)

```python
# Příklady
search_medicine(query="ibuprofen", limit=10)
# → [{'sukl_code': '12345', 'name': 'IBUPROFEN TABLETA 400MG', 'match_score': 30.0, 'match_type': 'exact', ...}, ...]

search_medicine(query="ibuprofn", use_fuzzy=True)  # Oprava překlepu
# → [{'name': 'IBUPROFEN...', 'match_type': 'fuzzy', 'fuzzy_score': 85.0, ...}, ...]
```

### 2. `get_medicine_details` - Detaily konkrétního přípravku
Kompletní informace o léčivém přípravku včetně složení a registračních údajů.

```python
get_medicine_details(sukl_code="12345")
# → {'name': '...', 'dosage_form': '...', 'composition': [...], ...}
```

### 3. `get_pil_content` - Příbalové informace (PIL)
Automatická extrakce textu z příbalového letáku (PDF/DOCX) s cachingem (24h TTL, 50 docs).

**Features:**
- Automatické parsování PDF (do 100 stran) a DOCX dokumentů
- Content-Type detection s fallback na URL extension
- LRU cache (50 dokumentů, 24h TTL)
- Graceful error handling s fallback na URL

```python
get_pil_content(sukl_code="12345")
# → {'sukl_code': '12345', 'full_text': 'Přečtěte si pozorně...', 'document_format': 'pdf', 'url': 'https://...'}
```

### 4. `get_spc_content` - Souhrn údajů o přípravku (SPC)
Odborné informace pro zdravotnické pracovníky (farmakologie, indikace, kontraindikace).

```python
get_spc_content(sukl_code="12345")
# → {'sukl_code': '12345', 'full_text': 'Souhrn údajů o přípravku...', 'document_format': 'pdf'}
```

### 5. `check_availability` - Dostupnost a alternativy
Kontrola dostupnosti s automatickým doporučením náhradních léků při nedostupnosti.

**Features:**
- Normalizace stavu dostupnosti (available/unavailable/unknown)
- Automatické hledání alternativ: stejná účinná látka → stejná ATC skupina
- Multi-kriteriální ranking: forma (40%), síla (30%), cena (20%), název (10%)
- Obohacení o cenové údaje a doplatky pacienta

```python
check_availability(sukl_code="12345", include_alternatives=True, limit=5)
# → {
#     'available': False,
#     'status': 'unavailable',
#     'alternatives': [
#         {'name': 'Alternative A', 'relevance_score': 85.2, 'patient_copay': 45.50, ...},
#         {'name': 'Alternative B', 'relevance_score': 78.5, 'patient_copay': 50.00, ...}
#     ],
#     'recommendation': 'This medicine is unavailable. Consider Alternative A (relevance: 85.2/100)'
# }
```

### 6. `get_reimbursement` - Informace o úhradách
Úhradové kategorie a podmínky preskripce.

```python
get_reimbursement(sukl_code="12345")
# → {'reimbursed': True, 'category': 'A', 'prescription_required': True}
```

### 7. `find_pharmacies` - Vyhledávání lékáren
Vyhledávání lékáren podle lokace a dalších kritérií.

```python
find_pharmacies(city="Praha", limit=20)
# → [{'name': 'Lékárna U Anděla', 'address': '...', ...}, ...]
```

### 8. `get_atc_info` - ATC klasifikace
Anatomicko-terapeuticko-chemická klasifikace léčiv.

```python
get_atc_info(atc_code="N02")
# → {'code': 'N02BE01', 'name': 'Paracetamol', ...}
```

Detailní dokumentace všech tools: **[API Reference](docs/api-reference.md)**

---

## 🌐 REST API Integration (v5.0 - Experimental)

### Nově v5.0: SÚKL REST API Klient

Server nyní obsahuje experimentální podporu pro přímé volání SÚKL REST API (`prehledy.sukl.cz/v1`).

#### Dostupné REST API metody

```python
from sukl_mcp.api import get_rest_client

async with get_rest_client() as client:
    # Vyhledávání podle ATC kódu
    result = await client.search_medicines(atc="A10AE04", pocet=10)
    print(f"Nalezeno {result.celkem} léků")

    # Seznam lékáren
    pharmacies = await client.get_pharmacies(stranka=1, pocet=20)
    print(f"Celkem {pharmacies.celkem} lékáren")

    # Číselníky
    uhrad = await client.get_ciselnik("uhrady")
    atc_codes = await client.get_atc_codes()

    # Datum aktualizace
    dates = await client.get_update_dates()
    print(f"Data aktualizována: {dates.DLPO}")
```

#### ⚠️ Známá omezení

**POST /dlprc NEPODPORUJE name-based search**

SÚKL REST API akceptuje pouze strukturované filtry:
- `atc` - ATC kód (např. "A10AE04")
- `stavRegistrace` - Stav registrace (R, N, Z)
- `uhrada` - Kód úhrady (A, B, D)
- `jeDodavka` - Boolean (dostupnost)
- `jeRegulovany` - Boolean (regulované)

**Chybí**: Parametr pro vyhledávání podle názvu léku!

Proto:
- ✅ MCP tools používají **CSV klienta** (funguje perfektně)
- 📊 REST API je připravené pro budoucí strukturované dotazy
- 🔮 Plánováno: Hybrid architecture v budoucí verzi

#### Dokumentace

- **REST API Reference**: [`docs/sukl_api_dokumentace.md`](docs/sukl_api_dokumentace.md)
- **Unit Testy**: [`tests/test_rest_api_client.py`](tests/test_rest_api_client.py) (23 testů)

---

## 🏗️ Architektura

### Vícevrstvý design (v4.0 Hybrid Architecture)

```
┌─────────────────────────────────────────────────────────┐
│                      AI Agents                          │
│              (Claude, GPT-4, atd.)                      │
└────────────────────┬────────────────────────────────────┘
                     │ MCP Protocol
┌────────────────────▼────────────────────────────────────┐
│                FastMCP Server                           │
│         (8 MCP tools pro farmaceutická data)            │
└─────────────┬──────────────────────┬────────────────────┘
              │                      │
     ┌────────▼────────┐    ┌────────▼────────┐
     │ SUKLAPIClient   │    │  SUKLClient     │
     │  (REST API)     │    │  (CSV Fallback) │
     │ • Cache (5min)  │    │ • In-memory     │
     │ • Rate limit    │    │ • pandas DF     │
     │ • Retry logic   │    │ • Fuzzy search  │
     └────────┬────────┘    └────────┬────────┘
              │                      │
     ┌────────▼────────┐    ┌────────▼────────┐
     │  SÚKL REST API  │    │ SÚKL Open Data  │
     │ prehledy.sukl.cz│    │ opendata.sukl.cz│
     │  (Real-time)    │    │  (CSV v ZIP)    │
     └─────────────────┘    └─────────────────┘

     PRIMARY (3 tools)      FALLBACK (always)
     ✅ Fast (0-1ms p50)    ✅ Reliable (50ms)
     ✅ Real-time data      ✅ Price data (CAU)
     ⚠️  No price data      ⚠️  Monthly updates
```

### Klíčové komponenty

#### v4.0 Hybrid Architecture
- **`server.py`**: FastMCP server s dual-client initialization
- **`api/client.py`**: SUKLAPIClient pro REST API access (primary)
- **`api/models.py`**: Pydantic modely pro API responses
- **`client_csv.py`**: CSV client pro fallback + price data
- **`models.py`**: Pydantic modely pro MCP responses
- **`exceptions.py`**: Custom exception hierarchy

#### Migrace Status (Phase-01)
- ✅ **search_medicine** - Hybrid mode (REST → CSV fallback)
- ✅ **get_medicine_details** - Hybrid mode (REST + CSV price enrichment)
- ✅ **check_availability** - Hybrid mode (REST + CSV alternatives)
- 📄 **get_reimbursement** - CSV-only (REST API nemá CAU data)

Kompletní architektura: **[Architecture Documentation](docs/architecture.md)**

---

## 🚀 Deployment

### Option 1: FastMCP Cloud (Doporučeno)

Automatický deployment z GitHub repozitáře:

```bash
# 1. Push do main branch
git push origin main

# 2. Připojit repozitář na https://fastmcp.cloud/
# 3. Server automaticky deploynutý a dostupný
```

Server bude dostupný na: `https://your-project.fastmcp.app/mcp`

### Option 2: Smithery (Docker/HTTP)

Docker-based deployment s HTTP transportem:

```bash
# Build Docker image
docker build -t sukl-mcp:3.1.0 .

# Spustit kontejner
docker run -p 8000:8000 sukl-mcp:3.1.0

# Nasazení na Smithery
smithery deploy
```

### Option 3: Lokální development

```bash
# Stdio transport (pro Claude Desktop)
python -m sukl_mcp

# HTTP transport (pro remote clients)
MCP_TRANSPORT=http MCP_PORT=8000 python -m sukl_mcp
```

Detailní deployment instrukce: **[Deployment Guide](docs/deployment.md)**

---

## 🔧 Development

### Setup development prostředí

```bash
# Instalace s dev dependencies
pip install -e ".[dev]"

# Spustit testy
pytest tests/ -v

# Code formatting
black src/ tests/

# Linting
ruff check src/

# Type checking
mypy src/sukl_mcp/
```

### Makefile příkazy

```bash
make install      # Instalace projektu
make test         # Spuštění testů
make test-cov     # Testy s coverage reportem
make format       # Black code formatting
make lint         # Ruff + mypy kontrola
make clean        # Vyčištění build artifacts
make dev          # Format + test + lint (kompletní workflow)
```

### Struktura projektu

```
SUKL-mcp/
├── src/sukl_mcp/
│   ├── server.py               # FastMCP server + MCP tools
│   ├── api/                    # REST API module (v4.0)
│   │   ├── __init__.py
│   │   ├── client.py           # SUKLAPIClient
│   │   └── models.py           # API Pydantic models
│   ├── client_csv.py           # CSV client (fallback)
│   ├── models.py               # MCP response models
│   ├── exceptions.py           # Custom exceptions
│   ├── fuzzy_search.py         # Smart search engine
│   ├── price_calculator.py     # Price & reimbursement
│   ├── availability.py         # Availability & alternatives
│   ├── document_parser.py      # PDF/DOCX parser
│   └── __main__.py             # Entry point
├── tests/
│   ├── test_api_client.py      # REST API tests (22)
│   ├── test_hybrid_tools.py    # Integration tests (13)
│   ├── test_performance_benchmark.py  # Benchmarks (3)
│   ├── test_validation.py      # Input validation
│   ├── test_async_io.py        # Async I/O tests
│   ├── test_fuzzy_search.py    # Smart search tests
│   ├── test_availability.py    # Alternatives tests
│   ├── test_document_parser.py # Parser tests
│   └── ...                     # (241 total tests)
├── docs/                       # 125+ stránek dokumentace
│   ├── Phase-01-REST-API-Migration-Plan.md
│   ├── architecture.md
│   ├── api-reference.md
│   └── ...
├── pyproject.toml              # Project configuration
└── Makefile                    # Development commands
```

Developer guide: **[Developer Documentation](docs/developer-guide.md)**

---

## 🧪 Testing

Projekt obsahuje **241 comprehensive tests** pokrývající:

### Core Functionality (23 tests)
- ✅ Input validation (search query, SÚKL kódy, ATC prefixy)
- ✅ Async I/O behavior (non-blocking ZIP extraction)
- ✅ Race condition prevention (thread-safe initialization)
- ✅ ZIP bomb protection (max 5 GB)
- ✅ Regex injection prevention
- ✅ Environment configuration

### EPIC 1: Document Parser (47 tests)
- ✅ PDF/DOCX download and parsing
- ✅ LRU cache mechanics
- ✅ Security features (size limits, timeouts)
- ✅ Error handling and graceful degradation

### EPIC 2: Smart Search (34 tests)
- ✅ Multi-level search pipeline
- ✅ Fuzzy matching with rapidfuzz
- ✅ Scoring system and ranking
- ✅ Match type detection

### EPIC 3: Price & Reimbursement (44 tests)
- ✅ Price data extraction and validation
- ✅ Patient copay calculation
- ✅ Date parsing and validity filtering
- ✅ Numeric conversion with graceful handling

### EPIC 4: Availability & Alternatives (49 tests)
- ✅ Availability normalization
- ✅ Strength parsing and similarity
- ✅ Multi-criteria ranking algorithm
- ✅ Alternative medicine recommendations

### REST API Layer (22 tests)
- ✅ SUKLAPIClient unit tests
- ✅ Cache mechanics and TTL
- ✅ Rate limiting
- ✅ Error handling and retries

### Integration Tests (13 tests)
- ✅ Hybrid REST API + CSV fallback workflows
- ✅ Real API integration tests
- ✅ Data consistency validation
- ✅ End-to-end tool testing

### Performance Benchmarks (3 tests)
- ✅ search_medicine performance (REST vs CSV)
- ✅ get_medicine_details throughput (181 ops/sec)
- ✅ check_availability with alternatives workflow

```bash
# Spustit všechny testy
pytest tests/ -v

# S coverage reportem
pytest tests/ -v --cov=sukl_mcp --cov-report=html

# Konkrétní test suite
pytest tests/test_api_client.py -v          # REST API tests
pytest tests/test_hybrid_tools.py -v        # Integration tests
pytest tests/test_performance_benchmark.py  # Performance benchmarks
```

**Test coverage**: >85% (všechny moduly)
**Pass rate**: 264/264 tests passing (100%) - 241 původních + 23 REST API testů

---

## 📚 Dokumentace

Kompletní dokumentace v **[docs/](docs/)** adresáři:

### Pro vývojáře
- **[Product Specification](PRODUCT_SPECIFICATION.md)** - 📋 Vize, architektura, roadmapa vývoje
- **[Getting Started](docs/index.md)** - Rychlý úvod a instalace
- **[Architecture](docs/architecture.md)** - Systémová architektura (6 Mermaid diagramů)
- **[API Reference](docs/api-reference.md)** - Kompletní dokumentace 8 MCP tools + 5 resources
- **[Developer Guide](docs/developer-guide.md)** - Development setup a workflow
- **[Examples](docs/examples.md)** - 15 code examples

### Pro operations
- **[Deployment](docs/deployment.md)** - FastMCP Cloud + Smithery + Docker
- **[Data Reference](docs/data-reference.md)** - SÚKL Open Data struktura

### Pro uživatele
- **[User Guide](docs/user-guide.md)** - Konfigurace Claude Desktop a použití

---

## 🛡️ Security Features

### Implementované bezpečnostní prvky

1. **ZIP Bomb Protection**
   - Max velikost: 5 GB
   - Kontrola před extrakcí
   - Custom exception: `SUKLZipBombError`

2. **Regex Injection Prevention**
   - Všechny search queries jako literal strings
   - `regex=False` v pandas operations
   - Input sanitization

3. **Input Validation**
   - Query délka: max 200 znaků
   - SÚKL kód: pouze číslice, max 7 znaků
   - Limit range: 1-100
   - Custom exception: `SUKLValidationError`

4. **Thread Safety**
   - Race condition prevention s `asyncio.Lock`
   - Double-checked locking pattern
   - Singleton client instance

---

## 🌍 Technologie

### Core Stack

- **[FastMCP](https://gofastmcp.com)** 2.14+ - MCP protocol framework
- **[Pydantic](https://pydantic.dev)** 2.0+ - Data validation a serialization
- **[pandas](https://pandas.pydata.org)** 2.0+ - In-memory data processing
- **[httpx](https://www.python-httpx.org)** - Async HTTP client

### Development Tools

- **pytest** - Testing framework
- **black** - Code formatting
- **ruff** - Linting
- **mypy** - Type checking

### Infrastructure

- **FastMCP Cloud** - Managed MCP server hosting
- **Smithery** - Docker/HTTP deployment platform
- **GitHub Actions** - CI/CD pipeline

---

## 📊 Datový zdroj

Všechna data pochází z oficiálního SÚKL Open Data portálu:

- **URL**: https://opendata.sukl.cz
- **Licence**: Open Data - volné použití s atribucí
- **Aktualizace**: Měsíční (typicky kolem 23. dne)
- **Formát**: CSV soubory v ZIP archivu (Windows-1250 encoding)
- **Velikost**: ~50 MB komprimované, ~200 MB rozzipované

### Datové soubory

- `DLP.csv` - Databáze léčivých přípravků
- `DLP_Slozeni.csv` - Složení přípravků (účinné látky)
- `DLP_Latky.csv` - Slovník léčivých látek
- `DLP_ATC.csv` - ATC klasifikace
- `DLP_Dokumenty.csv` - Odkazy na PIL/SPC dokumenty

Detaily: **[Data Reference](docs/data-reference.md)**

---

## ⚠️ Právní upozornění

Tento server poskytuje informace výhradně pro informační účely. Data mohou být zpožděná a neměla by nahrazovat konzultaci s lékařem nebo lékárníkem. Vždy konzultujte zdravotnického profesionála pro lékařskou radu.

Oficiální a právně závazné informace naleznete přímo na https://www.sukl.cz.

---

## 🤝 Contributing

Vítáme příspěvky! Přečtěte si [CONTRIBUTING.md](CONTRIBUTING.md) pro:

- Coding standards (black, ruff, mypy)
- Commit message format (Conventional Commits)
- Testing requirements (>80% coverage)
- Pull request process

---

## 📄 License

MIT License - viz [LICENSE](LICENSE) soubor.

Data poskytnutá SÚKL pod podmínkami Open Data: https://opendata.sukl.cz/?q=podminky-uziti

---

## 🔗 Odkazy

- **FastMCP Framework**: https://gofastmcp.com
- **SÚKL Open Data**: https://opendata.sukl.cz
- **Model Context Protocol**: https://modelcontextprotocol.io
- **Issues & Support**: https://github.com/DigiMedic/SUKL-mcp/issues

---

**Vytvořeno pomocí [FastMCP](https://gofastmcp.com)** | **Data od [SÚKL](https://opendata.sukl.cz)**
