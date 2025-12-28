# SÚKL MCP Server 🏥💊

FastMCP server poskytující AI agentům přístup k české databázi léčivých přípravků (SÚKL).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.14+-green.svg)](https://gofastmcp.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Co tento server umožňuje

Díky tomuto MCP serveru mohou AI agenti (např. Claude) bezpečně a spolehlivě:

- **Vyhledávat léčiva** podle názvu, účinné látky nebo ATC kódu
- **Získat detaily přípravku** včetně složení, registrace a dokumentů
- **Zobrazit příbalový leták** (PIL) s informacemi pro pacienty
- **Zkontrolovat dostupnost** léčiva na českém trhu
- **Zjistit úhrady** - kolik platí pojišťovna a jaký je doplatek
- **Najít lékárny** včetně pohotovostních a e-shopů

## 📦 Instalace

### Ze zdrojového kódu

```bash
cd sukl_mcp
python -m venv venv
source venv/bin/activate  # Linux/Mac
# nebo: venv\Scripts\activate  # Windows

pip install -e ".[all]"
```

## 🚀 Rychlý start

### Spuštění serveru

```bash
# V aktivovaném virtuálním prostředí
sukl-mcp

# Nebo přímo
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

### Použití jako Python knihovny

```python
import asyncio
from sukl_mcp import SUKLClient

async def main():
    async with SUKLClient() as client:
        # Vyhledání léčiva
        results = await client.search_medicines("ibuprofen", limit=5)
        for med in results:
            print(f"{med.get('nazev')} - {med.get('atc', 'N/A')}")

        # Detail přípravku
        detail = await client.get_medicine_detail("0012345")
        if detail:
            print(f"Dostupnost: {detail.get('dostupnost')}")

asyncio.run(main())
```

## 🛠️ Dostupné nástroje (MCP Tools)

### `search_medicine`
Vyhledává léčivé přípravky v databázi.

**Parametry:**
- `query`: Hledaný text (název, účinná látka, ATC kód)
- `only_available`: Pouze dostupné přípravky (default: false)
- `only_reimbursed`: Pouze hrazené pojišťovnou (default: false)
- `limit`: Max počet výsledků (default: 20)

**Příklad:** "Najdi všechny přípravky s ibuprofem, které jsou hrazené pojišťovnou"

### `get_medicine_details`
Vrací kompletní informace o léčivém přípravku.

**Parametry:**
- `sukl_code`: 7-místný SÚKL kód (např. "0012345")

**Příklad:** "Jaké jsou detaily přípravku s kódem 0012345?"

### `get_pil_content`
Získá odkaz na příbalový leták pro pacienty.

**Parametry:**
- `sukl_code`: SÚKL kód přípravku

**Příklad:** "Ukaž mi příbalový leták pro Paralen"

### `check_availability`
Kontroluje dostupnost léčiva na trhu.

**Parametry:**
- `sukl_code`: SÚKL kód přípravku

**Příklad:** "Je Ibuprofen 400 aktuálně dostupný?"

### `get_reimbursement`
Informace o úhradě zdravotní pojišťovnou.

**Parametry:**
- `sukl_code`: SÚKL kód přípravku

**Příklad:** "Kolik je doplatek na tento lék?"

### `find_pharmacies`
Vyhledává lékárny podle kritérií.

**Parametry:**
- `city`: Název města (volitelné)
- `postal_code`: PSČ (volitelné)
- `has_24h_service`: Pouze pohotovostní (default: false)
- `has_internet_sales`: Pouze s e-shopem (default: false)
- `limit`: Max počet výsledků (default: 20)

**Příklad:** "Najdi pohotovostní lékárny v Praze"

### `get_atc_info`
Informace o ATC klasifikační skupině.

**Parametry:**
- `atc_code`: ATC kód (1-7 znaků)

**Příklad:** "Co je skupina N02 v ATC klasifikaci?"

## 📊 Zdroje dat

Server využívá oficiální zdroje SÚKL:

| Zdroj | URL | Aktualizace |
|-------|-----|-------------|
| REST API | prehledy.sukl.cz | Real-time |
| Open Data | opendata.sukl.cz | Měsíčně |

## ⚙️ Konfigurace

### Proměnné prostředí

```bash
# API timeouts
SUKL_TIMEOUT_SECONDS=30
SUKL_CONNECT_TIMEOUT=10

# Cache
SUKL_CACHE_ENABLED=true
SUKL_CACHE_TTL_SECONDS=3600

# Rate limiting
SUKL_MAX_REQUESTS_PER_MINUTE=60
```

## 🧪 Vývoj

### Nastavení vývojového prostředí

```bash
# Virtuální prostředí (pokud ještě není aktivní)
python -m venv venv
source venv/bin/activate  # Linux/Mac

# Instalace s dev závislostmi
pip install -e ".[dev]"
```

### Spuštění testů

```bash
# Všechny testy
pytest tests/ -v

# S pokrytím kódu
pytest tests/ -v --cov=sukl_mcp --cov-report=html

# Pouze unit testy (bez sítě)
pytest tests/ -v -m "not integration"
```

### Formátování a linting

```bash
# Formátování
black src/ tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/
```

## 📝 Architektura

Server je postaven na třech hlavních modulech:

1. **models.py** - Pydantic modely pro validaci dat
2. **client.py** - HTTP klient s cachováním a rate limitingem
3. **server.py** - FastMCP server s MCP tools

```
sukl_mcp/
├── src/sukl_mcp/
│   ├── __init__.py
│   ├── models.py      # Pydantic modely
│   ├── client.py      # SÚKL API klient
│   └── server.py      # FastMCP server
├── tests/
│   └── test_sukl_mcp.py
├── pyproject.toml
└── README.md
```

## 📜 Právní upozornění

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

## 📜 Licence

MIT License - viz [LICENSE](../LICENSE)

## 🙏 Poděkování

- [SÚKL](https://www.sukl.cz) za poskytování otevřených dat
- [FastMCP](https://gofastmcp.com) za skvělý MCP framework
- [Anthropic](https://www.anthropic.com) za MCP specifikaci

---

**Vytvořeno s ❤️ pro české zdravotnictví**
