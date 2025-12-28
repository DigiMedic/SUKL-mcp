# CLAUDE.md

Tento soubor poskytuje pokyny pro Claude Code (claude.ai/code) při práci s kódem v tomto úložišti.

## Přehled projektu

**Python SÚKL MCP Server** - Produkční MCP server pro přístup k české farmaceutické databázi SÚKL.

## Architektura

### Struktura projektu
```
fastmcp-boilerplate/
├── src/sukl_mcp/
│   ├── server.py       # FastMCP server s 7 MCP tools
│   ├── client_csv.py   # CSV data loader a klient
│   ├── models.py       # Pydantic modely pro validaci
│   ├── exceptions.py   # Custom exception types
│   └── __init__.py     # Public API exports
├── tests/
│   ├── test_validation.py  # Input validation testy
│   └── test_async_io.py    # Async I/O testy
├── pyproject.toml      # Konfigurace projektu
├── fastmcp.yaml        # FastMCP Cloud deployment
├── smithery.yaml       # Smithery deployment
└── Dockerfile          # Docker kontejner
```

### Datový tok
```
SÚKL Open Data (ZIP) → SUKLDataLoader → pandas DataFrames →
SUKLClient (search/filter) → FastMCP Server (7 tools) → AI Agent
```

### Klíčové komponenty

**`client_csv.py`** - Data loader a klient:
- `SUKLDataLoader`: Stahuje a extrahuje ZIP (async), načítá CSV do pandas
- `SUKLClient`: Vyhledávání léků, detail přípravku, ATC skupiny
- `get_sukl_client()`: Thread-safe singleton s asyncio.Lock
- Bezpečnost: ZIP bomb protection, regex injection prevention

**`server.py`** - FastMCP server:
- 7 MCP tools: search_medicine, get_medicine_details, get_pil_content, check_availability, get_reimbursement, find_pharmacies, get_atc_info
- Lifecycle management přes `@asynccontextmanager`
- Pydantic validace všech vstupů
- Input validace: délka query, formát SÚKL kódu, rozsah limitů

**`models.py`** - Type-safe datové modely:
- MedicineSearchResult, MedicineDetail, ATCGroup, PharmacyInfo
- Pydantic 2.0+ s runtime validací

## Vývojové příkazy

### Instalace a spuštění
```bash
# Vytvoření virtuálního prostředí
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Instalace v režimu vývoje
pip install -e ".[dev]"

# Spuštění serveru
python -m sukl_mcp.server
```

### Testování
```bash
# Spuštění všech testů
pytest tests/ -v

# S coverage reportem
pytest tests/ -v --cov=src/sukl_mcp --cov-report=term-missing

# Konkrétní test
pytest tests/test_validation.py -v
```

### Code quality
```bash
# Formátování kódu
black src/

# Linting
ruff check src/

# Type checking
mypy src/
```

## Klíčové vzory

### Přidání nových MCP tools
1. **Definice tool funkce** v `server.py`:
```python
@mcp.tool()
async def my_new_tool(query: str, limit: int = 10) -> dict:
    """Popis nástroje pro AI agenta."""
    # Input validace
    if not query or len(query) > 200:
        raise ValueError("Neplatný query")

    # Získání klienta
    client = await get_sukl_client()

    # Business logika
    results = await client.my_method(query, limit)
    return {"results": results}
```

2. **Přidání metody do SUKLClient** v `client_csv.py`:
```python
async def my_method(self, query: str, limit: int) -> list[dict]:
    """Implementace business logiky."""
    df = self._data.get("table_name")
    # Filtering, searching, atd.
    return df.head(limit).to_dict('records')
```

3. **Testy** v `tests/test_my_tool.py`:
```python
@pytest.mark.asyncio
async def test_my_new_tool():
    result = await my_new_tool("test", limit=5)
    assert len(result["results"]) <= 5
```

### Async I/O best practices

**Blokující operace musí běžet v executoru:**
```python
import asyncio

async def blocking_operation():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, sync_function)
    return result
```

**Paralelní async operace:**
```python
results = await asyncio.gather(
    operation1(),
    operation2(),
    operation3()
)
```

### Bezpečnostní vzory

**Input validace:**
```python
if len(query) > 200:
    raise SUKLValidationError("Query příliš dlouhý")
if not sukl_code.isdigit():
    raise SUKLValidationError("SÚKL kód musí být číselný")
```

**Regex injection prevention:**
```python
# ŠPATNĚ:
df['NAZEV'].str.contains(user_input, case=False, na=False)

# SPRÁVNĚ:
df['NAZEV'].str.contains(user_input, case=False, na=False, regex=False)
```

**ZIP bomb protection:**
```python
total_size = sum(info.file_size for info in zip_ref.infolist())
if total_size > 5 * 1024 * 1024 * 1024:  # 5 GB
    raise SUKLZipBombError(f"ZIP příliš velký: {total_size}")
```

**Thread-safe singleton:**
```python
_client: Optional[SUKLClient] = None
_client_lock: asyncio.Lock = asyncio.Lock()

async def get_sukl_client() -> SUKLClient:
    global _client
    if _client is not None:
        return _client

    async with _client_lock:
        if _client is None:
            _client = SUKLClient()
            await _client.initialize()
    return _client
```

## Konfigurace prostředí

### Environment variables
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

### Použití v Claude Desktop
Přidejte do `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "sukl": {
      "command": "python",
      "args": ["-m", "sukl_mcp.server"],
      "env": {
        "PYTHONPATH": "/cesta/k/fastmcp-boilerplate/src"
      }
    }
  }
}
```

## Testování

**Filozofie**: Testujte business logiku, ne FastMCP protokol. Framework zajišťuje MCP compliance.

**Zaměřte se na:**
- Input validaci (test_validation.py)
- Async I/O chování (test_async_io.py)
- Data transformace
- Error handling

## Poznámky pro vývoj

**Vždy používejte virtuální prostředí:**
```bash
source venv/bin/activate  # před každou prací
```

**Type safety:**
- Všechny funkce mají type hints
- `mypy` kontroluje staticky
- Pydantic validuje runtime

**Performance:**
- CSV data načítána jednou při inicializaci (68,248 záznamů)
- Pandas in-memory queries (rychlejší než SQL pro tento rozsah)
- Async I/O pro ZIP download a extraction

**Data freshness:**
- SÚKL data aktualizována měsíčně
- ZIP cache v `/tmp` - smazat pro refresh
