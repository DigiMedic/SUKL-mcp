# SÚKL MCP Server

**Production-ready FastMCP server** poskytující přístup k české databázi léčivých přípravků SÚKL (Státní ústav pro kontrolu léčiv).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.14+-green.svg)](https://gofastmcp.com)
[![Version](https://img.shields.io/badge/version-2.0.0-brightgreen.svg)](https://github.com/your-org/fastmcp-boilerplate/blob/main/CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-23%20passed-success.svg)](sukl_mcp/tests/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **v2.0.0** - Kompletně přepracovaný Python-only projekt s bezpečnostními vylepšeními, async I/O a 23 testy. [Co je nového?](CHANGELOG.md)

## Funkce

- **Vyhledávání léčivých přípravků** podle názvu, účinné látky nebo ATC kódu
- **Detailní informace** o léčivých přípravcích včetně složení a registrace
- **Příbalové letáky (PIL)** s informacemi pro pacienty
- **Informace o dostupnosti** na českém trhu
- **Informace o úhradách** a doplatcích
- **Vyhledávání lékáren** podle lokace a služeb
- **ATC klasifikace** léčivých látek

## Rozsah dat

Server pracuje s aktuálními daty z SÚKL Open Data:

- **68,248** registrovaných léčivých přípravků
- **787,877** záznamů složení
- **3,352** léčivých látek
- **6,907** ATC klasifikačních kódů
- **61,240** dokumentů (PIL/SPC)

*Data aktualizována: 23. prosince 2024*

## ✨ Klíčové vlastnosti v2.0

### 🔒 Bezpečnost
- **ZIP bomb protection** - automatická detekce příliš velkých archivů (max 5 GB)
- **Regex injection prevention** - ochrana proti útokům přes search query
- **Input validace** - kompletní validace všech vstupních parametrů
- **Custom exceptions** - typované chyby pro lepší error handling

### ⚡ Performance
- **Async I/O** - non-blocking ZIP extraction a CSV loading
- **Paralelní načítání** - 5 CSV souborů načteno současně (3-5x rychlejší)
- **In-memory queries** - pandas DataFrames pro okamžité vyhledávání
- **Thread-safe** - race condition protection s asyncio.Lock

### 🛠️ Developer Experience
- **Environment variables** - konfigurace přes `SUKL_*` ENV proměnné
- **23 testů** - kompletní test coverage pro validaci a async I/O
- **Type safety** - Pydantic 2.0 modely s runtime validací
- **Čistá architektura** - Python-only bez TypeScript dependencies

## Instalace

### Požadavky

- Python 3.10+
- pip
- virtuální prostředí (doporučeno)

### Instalace ze zdrojového kódu

```bash
# Klonování repozitáře
git clone https://github.com/your-repo/fastmcp-boilerplate.git
cd fastmcp-boilerplate

# Vytvoření virtuálního prostředí
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Instalace serveru
cd sukl_mcp
pip install -e ".[dev]"
```

## Spuštění

### Rychlý start

```bash
# Aktivovat virtuální prostředí
source venv/bin/activate

# Spustit server
python -m sukl_mcp.server
```

### Použití v Claude Desktop

Přidejte do `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sukl": {
      "command": "python",
      "args": [
        "-m",
        "sukl_mcp.server"
      ],
      "env": {
        "PYTHONPATH": "/cesta/k/fastmcp-boilerplate/sukl_mcp/src"
      }
    }
  }
}
```

### Nasazení na FastMCP Cloud

Server je připraven pro nasazení na [FastMCP Cloud](https://gofastmcp.com):

```bash
# 1. Přihlášení do FastMCP Cloud
fastmcp login

# 2. Deploy serveru
cd sukl_mcp
fastmcp deploy

# Server bude dostupný na:
# https://your-server.fastmcp.cloud
```

**Konfigurace:** Projekt obsahuje `fastmcp.yaml` s optimalizovaným nastavením pro cloud deployment:
- ✅ Absolutní importy (fix pro "attempted relative import" chybu)
- ✅ Environment variables pro cache paths
- ✅ Python 3.10+ runtime
- ✅ Všechny dependencies (fastmcp, httpx, pydantic, pandas)

**Poznámka:** Pro FastMCP Cloud je důležité používat **absolutní importy** (`from sukl_mcp.server import mcp`), ne relativní (`from .server import mcp`).

### Použití jako Python knihovny

```python
import asyncio
from sukl_mcp.client_csv import SUKLClient

async def main():
    client = SUKLClient()
    await client.initialize()

    # Vyhledání léčiva
    results = await client.search_medicines("ibuprofen", limit=5)
    for med in results:
        print(f"{med.get('NAZEV')} - {med.get('ATC_WHO', 'N/A')}")

    # Detail přípravku
    detail = await client.get_medicine_detail("254045")
    if detail:
        print(f"Název: {detail.get('NAZEV')}")
        print(f"Síla: {detail.get('SILA')}")

    await client.close()

asyncio.run(main())
```

## MCP Tools

Server poskytuje následující MCP tools:

### `search_medicine`
Vyhledává léčivé přípravky v databázi.

**Parametry:**
- `query`: Hledaný text (název, účinná látka, ATC kód)
- `only_available`: Pouze dostupné přípravky (default: false)
- `only_reimbursed`: Pouze hrazené pojišťovnou (default: false)
- `limit`: Max počet výsledků (default: 20)

### `get_medicine_details`
Vrací kompletní informace o léčivém přípravku.

**Parametry:**
- `sukl_code`: 7-místný SÚKL kód (např. "0254045" nebo "254045")

### `get_pil_content`
Získá odkaz na příbalový leták pro pacienty.

### `check_availability`
Kontroluje dostupnost léčiva na trhu.

### `get_reimbursement`
Informace o úhradě zdravotní pojišťovnou.

### `find_pharmacies`
Vyhledává lékárny podle kritérií.

### `get_atc_info`
Informace o ATC klasifikační skupině.

## Architektura

```
sukl_mcp/
├── src/sukl_mcp/
│   ├── server.py       # FastMCP server s 7 MCP tools
│   ├── client_csv.py   # CSV data loader
│   ├── models.py       # Pydantic modely
│   └── __init__.py
├── tests/
│   ├── test_validation.py
│   └── test_async_io.py
├── pyproject.toml      # Python projekt konfigurace
└── README.md
```

## Datový tok

```
┌─────────────────┐
│  SÚKL Open Data │
│  (opendata.sukl │
│      .cz)       │
└────────┬────────┘
         │ Download ZIP
         ▼
┌─────────────────┐
│  SUKLDataLoader │
│  (client_csv.py)│
│                 │
│  • Download     │
│  • Extract      │
│  • Load CSV     │
└────────┬────────┘
         │ pandas DataFrames
         ▼
┌─────────────────┐
│   SUKLClient    │
│  (client_csv.py)│
│                 │
│  • search       │
│  • get_detail   │
│  • get_atc      │
└────────┬────────┘
         │ Python dicts
         ▼
┌─────────────────┐
│  FastMCP Server │
│   (server.py)   │
│                 │
│  • MCP Tools    │
│  • Pydantic     │
└────────┬────────┘
         │ MCP Protocol
         ▼
┌─────────────────┐
│   AI Agent      │
│  (Claude, etc.) │
└─────────────────┘
```

## Konfigurace

### Proměnné prostředí

```bash
# Data paths
export SUKL_CACHE_DIR=/var/cache/sukl
export SUKL_DATA_DIR=/var/lib/sukl

# Data source
export SUKL_OPENDATA_URL=https://opendata.sukl.cz/soubory/SOD20251223/DLP20251223.zip
export SUKL_DOWNLOAD_TIMEOUT=120.0

# Logging
export SUKL_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## Vývoj

### Nastavení vývojového prostředí

```bash
# Virtuální prostředí
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# Instalace s dev závislostmi
cd sukl_mcp
pip install -e ".[dev]"
```

### Testování

```bash
# Spuštění testů
pytest tests/ -v

# S coverage
pytest tests/ -v --cov=src/sukl_mcp --cov-report=term-missing

# Konkrétní test
pytest tests/test_validation.py -v
```

### Formátování a linting

```bash
# Formátování
black src/

# Linting
ruff check src/

# Type checking
mypy src/
```

## Známá omezení

### 1. Lékárny (find_pharmacies)
DLP dataset neobsahuje informace o lékárnách. Tool vrací prázdný seznam.

**Řešení:** Implementovat separátní zdroj dat pro lékárny z https://opendata.sukl.cz/?q=katalog/seznam-lekaren

### 2. Detailní úhrady (get_reimbursement)
Základní DLP tabulka neobsahuje detailní informace o cenách a úhradách.

**Řešení:** Načíst dodatečné CSV soubory:
- `dlp_cau_scau.csv` - Ceny a úhrady pro ambulantní péči
- `dlp_cau_scup.csv` - Ceny pro ústavní péči
- `dlp_cau_sneh.csv` - Nehrazené přípravky

### 3. PIL/SPC dokumenty
Server vrací pouze URL odkazy na dokumenty, ne jejich obsah.

**Aktuální řešení:** URL ve formátu `https://prehledy.sukl.cz/pil/{sukl_code}.pdf`

## Právní upozornění

⚠️ **Důležité:**

- Informace poskytované tímto serverem mají **pouze informativní charakter**
- Vždy se řiďte pokyny **lékaře a lékárníka**
- Data pochází z veřejných zdrojů SÚKL a mohou být zpožděná
- Server **nenahrazuje** odbornou lékařskou konzultaci

### Licence dat

Data SÚKL jsou poskytována pod podmínkami [Open Data SÚKL](https://opendata.sukl.cz/?q=podminky-uziti):
- ✅ Volné šíření a kopírování
- ✅ Komerční využití
- ⚠️ Povinnost uvést SÚKL jako zdroj
- ❌ Zákaz měnit význam dat

## Licence

MIT License - viz [LICENSE](LICENSE)

## Poděkování

- [SÚKL](https://www.sukl.cz) za poskytování otevřených dat
- [FastMCP](https://gofastmcp.com) za skvělý MCP framework
- [Anthropic](https://www.anthropic.com) za MCP specifikaci

---

**Vytvořeno s ❤️ pro české zdravotnictví**

*Poslední aktualizace: 28. prosince 2024*
