# SÚKL MCP Server

**Production-ready FastMCP server** poskytující AI agentům přístup k oficiální české databázi léčivých přípravků SÚKL (Státní ústav pro kontrolu léčiv).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.14+-green.svg)](https://gofastmcp.com)
[![Version](https://img.shields.io/badge/version-2.1.0-brightgreen.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-23%20passed-success.svg)](tests/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **v2.1.0** - Kompletně přepracovaný projekt s dual deployment (FastMCP Cloud + Smithery), 125+ stránek dokumentace, async I/O a pokročilými bezpečnostními funkcemi. [Co je nového?](CHANGELOG.md)

---

## 📋 O projektu

SÚKL MCP Server je implementace [Model Context Protocol](https://modelcontextprotocol.io/) serveru, který umožňuje AI asistentům (jako Claude, GPT-4, atd.) přístup k aktuálním informacím o léčivých přípravcích registrovaných v České republice.

### Klíčové vlastnosti

- 🔍 **7 MCP tools** pro komplexní práci s farmaceutickými daty
- 💊 **68,248 léčivých přípravků** z SÚKL Open Data
- ⚡ **Async I/O** s pandas DataFrames pro rychlé vyhledávání
- 🔒 **Security features**: ZIP bomb protection, regex injection prevention
- 🎯 **Type-safe**: Pydantic modely s runtime validací
- 🚀 **Dual deployment**: FastMCP Cloud (stdio) + Smithery (HTTP/Docker)
- ✅ **23 comprehensive tests** s pytest a coverage >80%

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
git clone https://github.com/your-org/fastmcp-boilerplate.git
cd fastmcp-boilerplate

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
        "PYTHONPATH": "/cesta/k/fastmcp-boilerplate/src"
      }
    }
  }
}
```

Restart Claude Desktop a server bude k dispozici.

---

## 🛠️ MCP Tools

Server poskytuje 7 specializovaných nástrojů pro práci s farmaceutickými daty:

### 1. `search_medicines` - Vyhledávání léčivých přípravků
Fulltextové vyhledávání podle názvu, účinné látky nebo ATC kódu.

```python
# Příklad
search_medicines(query="ibuprofen", limit=10)
# → [{'sukl_code': '12345', 'name': 'IBUPROFEN TABLETA 400MG', ...}, ...]
```

### 2. `get_medicine_detail` - Detaily konkrétního přípravku
Kompletní informace o léčivém přípravku včetně složení a registračních údajů.

```python
get_medicine_detail(sukl_code="12345")
# → {'name': '...', 'dosage_form': '...', 'composition': [...], ...}
```

### 3. `get_pil_document` - Příbalové informace (PIL)
Stažení příbalového letáku konkrétního přípravku.

```python
get_pil_document(sukl_code="12345")
# → {'type': 'PIL', 'url': 'https://...', 'content': '...'}
```

### 4. `check_medicine_availability` - Dostupnost léků
Kontrola aktuální dostupnosti přípravku na trhu.

```python
check_medicine_availability(sukl_code="12345")
# → {'available': True, 'status': 'active', 'last_update': '2024-12-23'}
```

### 5. `get_reimbursement_info` - Informace o úhradách
Úhradové kategorie a podmínky preskripce.

```python
get_reimbursement_info(sukl_code="12345")
# → {'reimbursed': True, 'category': 'A', 'prescription_required': True}
```

### 6. `search_pharmacies` - Vyhledávání lékáren
Vyhledávání lékáren podle lokace a dalších kritérií.

```python
search_pharmacies(region="Praha", limit=20)
# → [{'name': 'Lékárna U Anděla', 'address': '...', ...}, ...]
```

### 7. `get_atc_groups` - ATC klasifikace
Anatomicko-terapeuticko-chemická klasifikace léčiv.

```python
get_atc_groups(atc_prefix="N02")
# → [{'code': 'N02BE01', 'name': 'Paracetamol', ...}, ...]
```

Detailní dokumentace všech tools: **[API Reference](docs/api-reference.md)**

---

## 🏗️ Architektura

### Vícevrstvý design

```
┌─────────────────────────────────────────────────────────┐
│                      AI Agents                          │
│              (Claude, GPT-4, atd.)                      │
└────────────────────┬────────────────────────────────────┘
                     │ MCP Protocol
┌────────────────────▼────────────────────────────────────┐
│                FastMCP Server                           │
│         (7 MCP tools pro farmaceutická data)            │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  SUKLClient                             │
│     (CSV data loading, in-memory queries)               │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              SÚKL Open Data                             │
│        (opendata.sukl.cz - CSV v ZIP)                   │
└─────────────────────────────────────────────────────────┘
```

### Klíčové komponenty

- **`server.py`**: FastMCP server s MCP tools registrací
- **`client_csv.py`**: Async data loader a query engine
- **`models.py`**: Pydantic modely pro type-safe data handling
- **`exceptions.py`**: Custom exception hierarchy

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
docker build -t sukl-mcp:2.1.0 .

# Spustit kontejner
docker run -p 8000:8000 sukl-mcp:2.1.0

# Deploy na Smithery
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
fastmcp-boilerplate/
├── src/sukl_mcp/
│   ├── server.py          # FastMCP server + MCP tools
│   ├── client_csv.py      # Data loader + query engine
│   ├── models.py          # Pydantic data models
│   ├── exceptions.py      # Custom exceptions
│   └── __main__.py        # Entry point
├── tests/
│   ├── test_validation.py # Input validation tests
│   └── test_async_io.py   # Async I/O tests
├── docs/                  # 125+ stránek dokumentace
├── pyproject.toml         # Project configuration
└── Makefile               # Development commands
```

Developer guide: **[Developer Documentation](docs/developer-guide.md)**

---

## 🧪 Testing

Projekt obsahuje 23 comprehensive tests pokrývající:

- ✅ Input validation (search query, SÚKL kódy, ATC prefixy)
- ✅ Async I/O behavior (non-blocking ZIP extraction)
- ✅ Race condition prevention (thread-safe initialization)
- ✅ ZIP bomb protection (max 5 GB)
- ✅ Regex injection prevention
- ✅ Environment configuration

```bash
# Spustit všechny testy
pytest tests/ -v

# S coverage reportem
pytest tests/ -v --cov=sukl_mcp --cov-report=html

# Konkrétní test suite
pytest tests/test_validation.py -v
```

**Test coverage**: >80% (cíl: 90%+)

---

## 📚 Dokumentace

Kompletní dokumentace v **[docs/](docs/)** adresáři:

### Pro vývojáře
- **[Getting Started](docs/index.md)** - Rychlý úvod a instalace
- **[Architecture](docs/architecture.md)** - Systémová architektura (6 Mermaid diagramů)
- **[API Reference](docs/api-reference.md)** - Kompletní dokumentace 7 MCP tools
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
- **Issues & Support**: https://github.com/your-org/fastmcp-boilerplate/issues

---

**Vytvořeno pomocí [FastMCP](https://gofastmcp.com)** | **Data od [SÚKL](https://opendata.sukl.cz)**
