# CLAUDE.md

Tento soubor poskytuje pokyny pro Claude Code (claude.ai/code) při práci s kódem v tomto úložišti.

## Přehled projektu

**SÚKL MCP Server v3.1.0** - Produkční FastMCP server poskytující AI agentům přístup k české databázi léčivých přípravků (68,248 záznamů). Implementuje Model Context Protocol s **8 specializovanými nástroji** pro vyhledávání léčiv, získávání detailů, kontrolu dostupnosti a práci s farmaceutickými daty.

## Klíčové vývojové příkazy

### Setup a instalace
```bash
# Vytvoření virtuálního prostředí
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Instalace s dev závislostmi
pip install -e ".[dev]"
```

### Spuštění serveru
```bash
# Lokální development (stdio)
python -m sukl_mcp

# Nebo pomocí Makefile
make run

# HTTP transport (pro testování Smithery deployu)
MCP_TRANSPORT=http MCP_PORT=8000 python -m sukl_mcp
```

### Testování
```bash
# Všechny testy
pytest tests/ -v

# S coverage reportem
make test-cov
# nebo
pytest tests/ -v --cov=sukl_mcp --cov-report=term-missing --cov-report=html

# Konkrétní test soubor
pytest tests/test_validation.py -v

# Konkrétní test
pytest tests/test_validation.py::test_search_query_validation -v
```

### Code quality
```bash
# Formátování (black)
make format
# nebo
black src/ tests/

# Linting (ruff + mypy)
make lint
# nebo
ruff check src/
mypy src/sukl_mcp/

# Kompletní dev workflow
make dev  # format + test + lint
```

### Čištění
```bash
make clean  # Vyčistí __pycache__, .pytest_cache, .mypy_cache, atd.
```

## Architektura projektu

### Vícevrstvý design

```
AI Agent → FastMCP Server → SUKLClient → pandas DataFrames → SÚKL Open Data (CSV)
```

### Klíčové komponenty a datový tok

**1. Data Acquisition Layer** (`client_csv.py:62-174`)
- `SUKLDataLoader`: Async stahování a extrakce ZIP archivu
- ZIP bomb protection: max 5 GB extracted size
- Paralelní načítání 5 CSV souborů přes `asyncio.gather()`
- Cache v `/tmp/sukl_dlp_cache`, data v `/tmp/sukl_dlp_data`

**2. Data Access Layer** (`client_csv.py:176-366`)
- `SUKLClient`: In-memory vyhledávání v pandas DataFrames
- Thread-safe singleton pattern s double-checked locking
- Input validace: query max 200 znaků, SÚKL kód pouze číslice max 7 znaků
- Regex injection prevention: `regex=False` v pandas operations

**3. API Layer** (`server.py`)
- 8 MCP tools registrovaných přes `@mcp.tool` dekorátor
- 5 MCP resources (3 statické + 2 dynamické resource templates)
- 3 MCP prompts pro běžné dotazy
- **FastMCP 2.14+ features**: Context logging, Progress reporting, readOnlyHint annotations, tags
- Lifecycle management přes `@asynccontextmanager`
- Pydantic modely pro type-safe responses
- Automatická detekce transportu (stdio vs HTTP)
- Middleware stack: ErrorHandling, RateLimiting, Timing, Logging

**4. Data Models** (`models.py`)
- Pydantic 2.0+ modely s runtime validací
- `MedicineSearchResult`, `MedicineDetail`, `SearchResponse`, atd.
- Enums: `RegistrationStatus`, `DispensationMode`, `AvailabilityStatus`

**5. Document Parser** (`document_parser.py`)
- Automatická extrakce textu z PDF/DOCX dokumentů
- LRU cache (50 dokumentů, 24h TTL)
- Size/page limity pro bezpečnost

**6. Fuzzy Search** (`fuzzy_search.py`)
- Multi-level search pipeline (účinná látka → exact → substring → fuzzy)
- Non-blocking s thread executor pro rapidfuzz operace
- Smart scoring s váhami pro dostupnost a úhradu

**7. Price Calculator** (`price_calculator.py`)
- Kalkulace doplatků pacienta z dlp_cau.csv
- Validity filtering podle reference_date

### MCP Tools (8)

| # | Tool | Tags | Popis |
|---|------|------|-------|
| 1 | `search_medicine` | `search`, `medicines` | Smart search s fuzzy matchingem |
| 2 | `get_medicine_details` | `detail`, `medicines` | Kompletní detail přípravku |
| 3 | `get_pil_content` | `documents`, `pil` | Příbalový leták (PIL) |
| 4 | `get_spc_content` | `documents`, `spc` | Souhrn údajů o přípravku (SPC) |
| 5 | `check_availability` | `availability`, `alternatives` | Dostupnost + inteligentní alternativy |
| 6 | `get_reimbursement` | `pricing`, `reimbursement` | Cenové a úhradové údaje |
| 7 | `find_pharmacies` | `pharmacies`, `search` | Vyhledávání lékáren |
| 8 | `get_atc_info` | `classification`, `atc` | ATC klasifikace |

> **FastMCP Annotations**: Všechny tools mají `readOnlyHint: True` pro přeskočení potvrzovacích dialogů v ChatGPT a lepší UX.

### MCP Resources (5)

| URI | Tags | Typ | Popis |
|-----|------|-----|-------|
| `sukl://health` | `system`, `monitoring` | Statický | Stav serveru |
| `sukl://statistics` | `system`, `statistics` | Statický | Statistiky databáze |
| `sukl://atc-groups/top-level` | `classification`, `atc`, `reference` | Statický | Hlavní ATC skupiny |
| `sukl://medicine/{sukl_code}` | `medicines`, `detail` | **Template** | Dynamický detail léčiva |
| `sukl://atc/{atc_code}` | `classification`, `atc` | **Template** | Dynamická ATC skupina |

### Struktura dat v paměti

Po inicializaci jsou v paměti tyto pandas DataFrames:

| Tabulka | Záznamy | Popis |
|---------|---------|-------|
| `dlp_lecivepripravky` | 68,248 | Hlavní databáze léčiv |
| `dlp_slozeni` | 787,877 | Složení přípravků (účinné látky) |
| `dlp_lecivelatky` | 3,352 | Slovník léčivých látek |
| `dlp_atc` | 6,907 | ATC klasifikace |
| `dlp_nazvydokumentu` | 61,240 | Odkazy na PIL/SPC dokumenty |

**Memory footprint**: ~360 MB (300 MB DataFrames + 60 MB runtime)

## Kritické návrhové vzory

### Thread-safe singleton s double-checked locking

**Problém**: Zabránit vytvoření více instancí SUKLClient při concurrent inicializaci.

**Implementace** (`client_csv.py:338-358`):
```python
_client: Optional[SUKLClient] = None
_client_lock: asyncio.Lock = asyncio.Lock()

async def get_sukl_client() -> SUKLClient:
    # Fast path - bez zámku pokud je již inicializováno
    if _client is not None:
        return _client

    # Slow path - zámek pro inicializaci
    async with _client_lock:
        # Re-check po získání zámku
        if _client is None:
            _client = SUKLClient()
            await _client.initialize()

    return _client
```

**Důležité**: Všechny MCP tools MUSÍ používat `await get_sukl_client()` místo přímé instance.

### Async I/O pro blokující operace

**Pravidlo**: I/O operace (ZIP extraction, CSV loading) MUSÍ běžet v executoru.

**Příklad** (`client_csv.py:111-133`):
```python
async def _extract_zip(self, zip_path: Path) -> None:
    def _sync_extract():
        """Synchronní extrakce s bezpečnostní kontrolou."""
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # ZIP bomb protection
            total_size = sum(info.file_size for info in zip_ref.infolist())
            if total_size > 5 * 1024 * 1024 * 1024:  # 5 GB
                raise SUKLZipBombError(...)
            zip_ref.extractall(self.config.data_dir)

    # Spusť v executoru aby neblokovala event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_extract)
```

**Kdy používat executor**:
- ✅ ZIP extraction (CPU-intensive)
- ✅ CSV loading (I/O-bound)
- ❌ pandas queries (rychlé in-memory operace)
- ❌ HTTP requests (použij httpx.AsyncClient)

### Bezpečnostní validace vstupů

**Všechny uživatelské vstupy MUSÍ být validovány** (`client_csv.py:211-257`):

```python
# Query validace
if not query or not query.strip():
    raise SUKLValidationError("Query nesmí být prázdný")
if len(query) > 200:
    raise SUKLValidationError(f"Query příliš dlouhý: {len(query)} znaků")

# SÚKL kód validace
if not sukl_code.isdigit():
    raise SUKLValidationError(f"SÚKL kód musí být číselný")
if len(sukl_code) > 7:
    raise SUKLValidationError(f"SÚKL kód příliš dlouhý")

# Limit validace
if not (1 <= limit <= 100):
    raise SUKLValidationError(f"Limit musí být 1-100")
```

### Regex injection prevention

**KRITICKÉ**: Vždy používat `regex=False` v pandas string operations.

```python
# ✅ SPRÁVNĚ (literal string match)
mask = df['NAZEV'].str.contains(query, case=False, na=False, regex=False)

# ❌ ŠPATNĚ (umožňuje regex injection)
mask = df['NAZEV'].str.contains(query, case=False, na=False)
```

**Důvod**: Bez `regex=False` může útočník zadat query jako `"((((a+)+)+)+)X"` a způsobit catastrophic backtracking (DoS).

## Přidání nového MCP tool

### 1. Definice v server.py

```python
@mcp.tool
async def my_new_tool(
    param1: str,
    param2: int = 10,
    optional_param: bool = False
) -> MyResponseModel:
    """
    Popis nástroje pro AI agenta (zobrazí se v MCP inspector).

    Args:
        param1: Popis parametru
        param2: Popis s defaultní hodnotou
        optional_param: Volitelný flag

    Returns:
        MyResponseModel s výsledky

    Examples:
        - my_new_tool("example")
        - my_new_tool("test", param2=20)
    """
    # 1. Input validace
    if not param1 or len(param1) > 200:
        raise SUKLValidationError("Neplatný param1")

    # 2. Získání klienta
    client = await get_sukl_client()

    # 3. Business logika (přes client metody)
    results = await client.my_client_method(param1, param2)

    # 4. Transformace na Pydantic model
    return MyResponseModel(
        data=results,
        total=len(results),
        timestamp=datetime.now()
    )
```

### 2. Přidání metody do SUKLClient (client_csv.py)

```python
async def my_client_method(
    self,
    param1: str,
    param2: int
) -> list[dict]:
    """Implementace business logiky."""
    # Input validace
    if not param1:
        raise SUKLValidationError("param1 je povinný")

    # Inicializace pokud potřeba
    if not self._initialized:
        await self.initialize()

    # Získání DataFrame
    df = self._loader.get_table("dlp_lecivepripravky")
    if df is None:
        return []

    # Filtering/searching
    mask = df['COLUMN'].str.contains(param1, case=False, na=False, regex=False)
    results = df[mask].head(param2)

    # Konverze na dict records
    return results.to_dict('records')
```

### 3. Pydantic model (models.py)

```python
class MyResponseModel(BaseModel):
    """Response pro my_new_tool."""
    data: list[dict]
    total: int
    timestamp: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [{"key": "value"}],
                "total": 1,
                "timestamp": "2024-12-29T12:00:00"
            }
        }
    )
```

### 4. Testy (tests/test_my_tool.py)

```python
import pytest
from sukl_mcp.server import my_new_tool
from sukl_mcp.exceptions import SUKLValidationError

@pytest.mark.asyncio
async def test_my_new_tool_success():
    """Test úspěšného volání."""
    result = await my_new_tool("test", param2=5)
    assert result.total >= 0
    assert len(result.data) <= 5

@pytest.mark.asyncio
async def test_my_new_tool_validation():
    """Test input validace."""
    with pytest.raises(SUKLValidationError):
        await my_new_tool("", param2=10)  # Prázdný param1

    with pytest.raises(SUKLValidationError):
        await my_new_tool("x" * 201)  # Příliš dlouhý
```

## Environment konfigurace

### Podporované ENV proměnné

```bash
# Data source
export SUKL_OPENDATA_URL="https://opendata.sukl.cz/soubory/SOD20251223/DLP20251223.zip"
export SUKL_DOWNLOAD_TIMEOUT=120.0

# Data paths (konfigurovatelné pro deployment)
export SUKL_CACHE_DIR=/var/cache/sukl
export SUKL_DATA_DIR=/var/lib/sukl

# Transport config
export MCP_TRANSPORT=stdio  # nebo http, sse, streamable-http
export MCP_HOST=0.0.0.0
export MCP_PORT=8000

# Logging
export SUKL_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Claude Desktop konfigurace

```json
{
  "mcpServers": {
    "sukl": {
      "command": "python",
      "args": ["-m", "sukl_mcp"],
      "env": {
        "PYTHONPATH": "/cesta/k/SUKL-mcp/src",
        "SUKL_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## Deployment strategie

### FastMCP Cloud (stdio)

**Config**: `fastmcp.yaml`
- Automatický deploy z GitHub main branch
- Absolutní importy v kódu: `from sukl_mcp.xxx import yyy`
- Stdio transport (default)

### Smithery (HTTP/Docker)

**Config**: `smithery.yaml` + `Dockerfile`
- Multi-stage Docker build pro menší image
- HTTP transport přes ENV: `MCP_TRANSPORT=http`
- Persistentní volumes pro cache (`/tmp/sukl_dlp_cache`)
- Non-root user (UID 1000)

### Lokální development

```bash
# stdio (pro Claude Desktop)
python -m sukl_mcp

# HTTP (pro testování API)
MCP_TRANSPORT=http MCP_PORT=8000 python -m sukl_mcp
```

## Performance optimalizace

### Aktuální charakteristiky

- **Inicializace**: ~31s (ZIP download + extract + CSV load)
- **Search latency**: 50-150ms (full DataFrame scan, O(n))
- **Memory**: ~360 MB
- **Concurrent requests**: ~100/s (CPU bound na DataFrame scans)

### Možné optimalizace (pro budoucnost)

1. **Dict-based index na SÚKL kód**: O(1) lookup místo O(n) scan
2. **SQLite + FTS5**: Pro dataset >100k záznamů
3. **Redis cache**: Pro opakované queries
4. **Chunked loading**: Načíst pouze aktivní přípravky při startu

### Co NEDĚLAT

- ❌ Nepoužívat SQL databázi pro aktuální velikost datasetu (68k záznamů)
- ❌ Neoptimalizovat předčasně - pandas je dostatečně rychlý
- ❌ Neindexovat všechny sloupce - paměťový overhead

## Běžné úlohy

### Aktualizace SÚKL dat

```bash
# 1. Smazat cache
rm -rf /tmp/sukl_dlp_cache/DLP.zip
rm -rf /tmp/sukl_dlp_data/*.csv

# 2. Aktualizovat URL v ENV nebo client_csv.py
export SUKL_OPENDATA_URL="https://opendata.sukl.cz/soubory/SODYYYYMMDD/DLPYYYYMMDD.zip"

# 3. Restart serveru (automaticky stáhne nová data)
python -m sukl_mcp
```

### Debug inicializace

```bash
# Zapnout DEBUG logging
export SUKL_LOG_LEVEL=DEBUG
python -m sukl_mcp

# Kontrola načtených dat
python -c "
import asyncio
from sukl_mcp.client_csv import get_sukl_client

async def check():
    client = await get_sukl_client()
    health = await client.health_check()
    print(health)

asyncio.run(check())
"
```

### Přidání nové CSV tabulky

1. **Aktualizovat `client_csv.py:140-146`**:
   ```python
   tables = [
       "dlp_lecivepripravky",
       "dlp_slozeni",
       # ... existující
       "dlp_nova_tabulka",  # Přidat zde
   ]
   ```

2. **Přidat metodu v SUKLClient**:
   ```python
   async def get_nova_data(self, filter: str) -> list[dict]:
       df = self._loader.get_table("dlp_nova_tabulka")
       if df is None:
           return []
       results = df[df['COLUMN'] == filter]
       return results.to_dict('records')
   ```

3. **Vytvořit MCP tool v server.py** (viz sekce "Přidání nového MCP tool")

## Testovací strategie

### Co testovat

- ✅ Input validaci (délka, formát, rozsah)
- ✅ Async I/O behavior (non-blocking operations)
- ✅ Race conditions (concurrent initialization)
- ✅ Security (ZIP bomb, regex injection)
- ✅ Error handling (custom exceptions)

### Co NE testovat

- ❌ FastMCP protokol (framework zodpovědnost)
- ❌ pandas DataFrame operace (library zodpovědnost)
- ❌ Pydantic validaci (library zodpovědnost)

### Příklady testů

```python
# Input validace
@pytest.mark.asyncio
async def test_search_query_too_long():
    with pytest.raises(SUKLValidationError, match="příliš dlouhý"):
        await search_medicines("x" * 201)

# Async I/O
@pytest.mark.asyncio
async def test_zip_extraction_non_blocking():
    start = time.time()
    task = asyncio.create_task(loader._extract_zip(zip_path))
    # Event loop by měl zůstat responzivní
    await asyncio.sleep(0.1)
    elapsed = time.time() - start
    assert elapsed < 0.2  # Neblokuje event loop

# Race condition
@pytest.mark.asyncio
async def test_concurrent_initialization():
    results = await asyncio.gather(*[get_sukl_client() for _ in range(10)])
    # Všechny vrací stejnou instanci
    assert len(set(id(r) for r in results)) == 1
```

## Troubleshooting

### Server se nespustí

```bash
# Kontrola závislostí
pip install -e ".[dev]"

# Kontrola Python verze (vyžaduje 3.10+)
python --version

# Debug mode
export SUKL_LOG_LEVEL=DEBUG
python -m sukl_mcp
```

### Timeout při stahování dat

```bash
# Zvýšit timeout
export SUKL_DOWNLOAD_TIMEOUT=300.0

# Nebo stáhnout ZIP manuálně
mkdir -p /tmp/sukl_dlp_cache
curl -o /tmp/sukl_dlp_cache/DLP.zip https://opendata.sukl.cz/...
```

### Vysoká spotřeba paměti

```bash
# Kontrola velikosti DataFrames
python -c "
import asyncio
from sukl_mcp.client_csv import get_sukl_client

async def check_memory():
    client = await get_sukl_client()
    for name, df in client._loader._data.items():
        print(f'{name}: {len(df)} rows, {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB')

asyncio.run(check_memory())
"
```

### Testy failují

```bash
# Vyčistit cache
make clean

# Re-instalace
pip install -e ".[dev]"

# Spustit jednotlivé testy
pytest tests/test_validation.py -v -s
```

## Dokumentace

Kompletní dokumentace v `docs/`:
- `architecture.md` - Systémová architektura (6 Mermaid diagramů)
- `api-reference.md` - Dokumentace 7 MCP tools
- `developer-guide.md` - Development setup a workflow
- `deployment.md` - FastMCP Cloud + Smithery + Docker
- `data-reference.md` - SÚKL Open Data struktura

## Code style pravidla

- **Formátování**: Black (line length 100)
- **Linting**: Ruff (pycodestyle + pyflakes + isort + bugbear)
- **Type checking**: mypy (strict mode, disallow_untyped_defs)
- **Docstrings**: Google style (Args, Returns, Examples)
- **Imports**: Absolutní importy (`from sukl_mcp.xxx import yyy`)
- **Async**: Vždy používat `async/await`, nikdy synchronní I/O v hlavním vlákně
- **Exceptions**: Custom hierarchy (`SUKLValidationError`, `SUKLZipBombError`, `SUKLDataError`)

## Poznámky k bezpečnosti

- **ZIP bomb protection**: Max 5 GB extracted size
- **Regex injection**: Vždy `regex=False` v pandas operations
- **Input sanitization**: Validace na entry pointu (MCP tools)
- **Non-root container**: UID 1000 v Dockeru
- **No secrets**: Žádné API klíče v kódu (všechny veřejná data)
- **HTTPS only**: Všechny downloady přes HTTPS

## Závěrečné tipy

1. **Vždy spouštěj testy před commitem**: `make dev`
2. **Používej type hints**: mypy kontroluje staticky
3. **Loguj důležité události**: startup, data loading, errors
4. **Nepřidávej zbytečné závislosti**: projekt je minimalistický
5. **Dokumentuj architektonická rozhodnutí**: v kódu nebo v docs/
6. **Optimalizuj až když je problém**: předčasná optimalizace = kořen všeho zla
