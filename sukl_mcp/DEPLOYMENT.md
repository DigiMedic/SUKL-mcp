# FastMCP Cloud Deployment Guide

Tento dokument poskytuje podrobné pokyny pro nasazení SÚKL MCP serveru na FastMCP Cloud.

## 🚀 Rychlý start

```bash
# 1. Přihlášení
fastmcp login

# 2. Deploy
cd sukl_mcp
fastmcp deploy
```

## 📋 Požadavky

- **FastMCP CLI** - nainstaluj přes `pip install fastmcp`
- **FastMCP Cloud account** - zaregistruj se na https://gofastmcp.com
- **Python 3.10+** - specifikováno v `fastmcp.yaml`

## 📝 Konfigurace (fastmcp.yaml)

Projekt obsahuje předkonfigurovaný `fastmcp.yaml`:

```yaml
server:
  module: sukl_mcp.server    # Absolutní import!
  instance: mcp

runtime:
  python: "3.10"

dependencies:
  - fastmcp>=2.14.0,<3.0.0
  - httpx>=0.27.0
  - pydantic>=2.0.0
  - pandas>=2.0.0

environment:
  SUKL_CACHE_DIR: /tmp/sukl_dlp_cache
  SUKL_DATA_DIR: /tmp/sukl_dlp_data
  SUKL_DOWNLOAD_TIMEOUT: "120.0"
```

## 🔧 Řešení problémů

### Chyba: "attempted relative import with no known parent package"

**Příčina:** Použití relativních importů (`from .module import ...`) namísto absolutních.

**Řešení:** ✅ Projekt již používá absolutní importy:
```python
# ✅ SPRÁVNĚ (absolutní import)
from sukl_mcp.server import mcp
from sukl_mcp.client_csv import get_sukl_client

# ❌ ŠPATNĚ (relativní import - nefunguje v cloud)
from .server import mcp
from .client_csv import get_sukl_client
```

### Chyba: "Module not found"

**Příčina:** Špatná struktura projektu nebo chybějící dependencies.

**Řešení:**
1. Zkontroluj, že všechny dependencies jsou v `fastmcp.yaml`
2. Zkontroluj, že `module: sukl_mcp.server` odpovídá skutečné struktuře
3. Ujisti se, že máš `__init__.py` v každém adresáři

### Chyba: "Failed to initialize"

**Příčina:** Chyba v lifecycle managementu nebo při načítání dat.

**Řešení:**
1. Zkontroluj logy: `fastmcp logs`
2. Ujisti se, že `server_lifespan` neblokuje startup
3. Zvýš `SUKL_DOWNLOAD_TIMEOUT` pokud download trvá dlouho

## 🏗️ Struktura projektu pro cloud

```
sukl_mcp/
├── fastmcp.yaml           # Cloud config
├── src/sukl_mcp/
│   ├── __init__.py        # Package init (může mít relativní importy)
│   ├── __main__.py        # Entry point (absolutní importy!)
│   ├── server.py          # MCP server (absolutní importy!)
│   ├── client_csv.py      # Data client (absolutní importy!)
│   ├── models.py          # Pydantic modely
│   └── exceptions.py      # Custom exceptions
├── tests/
└── pyproject.toml
```

## 📊 Monitoring

### Zobrazení logů
```bash
# Real-time logs
fastmcp logs --follow

# Poslední 100 řádků
fastmcp logs --tail 100
```

### Kontrola statusu
```bash
fastmcp status
```

### Metriky
```bash
fastmcp metrics
```

## 🔐 Environment Variables

Nastavení environment variables v cloud:

```bash
# Přes fastmcp.yaml (doporučeno)
environment:
  SUKL_CACHE_DIR: /tmp/sukl_dlp_cache
  SUKL_DATA_DIR: /tmp/sukl_dlp_data

# Nebo přes CLI
fastmcp env set SUKL_CACHE_DIR=/custom/path
```

## 🎯 Best Practices

### 1. Používej absolutní importy
```python
# ✅ Vždy
from sukl_mcp.server import mcp

# ❌ Nikdy v server.py, client_csv.py, atd.
from .server import mcp
```

### 2. Validuj lokálně před deploymentem
```bash
# Test import
python -c "from sukl_mcp.server import mcp; print(mcp.version)"

# Spusť lokálně
python -m sukl_mcp

# Testy
pytest tests/ -v
```

### 3. Použij environment variables
```python
# ✅ Konfigurovatelné
cache_dir = os.getenv("SUKL_CACHE_DIR", "/tmp/sukl_dlp_cache")

# ❌ Hardcoded
cache_dir = "/tmp/sukl_dlp_cache"
```

### 4. Loguj správně
```python
import logging
logger = logging.getLogger(__name__)

# ✅ Viditelné v cloud logs
logger.info("Server initialized")
logger.error("Failed to load data")

# ❌ Neviditelné
print("Server initialized")
```

## 🚦 Lifecycle management

Server používá FastMCP lifespan pro správnou inicializaci:

```python
@asynccontextmanager
async def server_lifespan(server):
    # Startup - načti data
    logger.info("Starting SÚKL MCP Server...")
    client = await get_sukl_client()

    yield  # Server běží

    # Shutdown - cleanup
    logger.info("Shutting down...")
    await close_sukl_client()
```

**Důležité:**
- Startup by neměl trvat > 30s
- Pokud ano, zvýš timeout nebo cachuj data jinak
- Všechny async operace musí být awaited

## 📈 Performance v cloud

### Cold start optimization
```python
# ✅ Lazy loading
async def get_data():
    if not _cache:
        _cache = await load_data()
    return _cache

# ❌ Load all at import
data = load_data()  # Blokuje import!
```

### Memory management
```python
# ✅ Generator pro velká data
def process_records():
    for record in large_dataset:
        yield process(record)

# ❌ Load all do memory
results = [process(r) for r in large_dataset]
```

## 🔄 CI/CD Integration

GitHub Actions example:

```yaml
name: Deploy to FastMCP Cloud

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install FastMCP CLI
        run: pip install fastmcp

      - name: Deploy
        run: |
          cd sukl_mcp
          fastmcp deploy --token ${{ secrets.FASTMCP_TOKEN }}
```

## 📚 Další zdroje

- [FastMCP Documentation](https://gofastmcp.com/getting-started/welcome)
- [FastMCP Cloud Dashboard](https://cloud.fastmcp.com)
- [SÚKL Open Data](https://opendata.sukl.cz)

## 🆘 Podpora

Máš problémy s deploymentem?

1. **Zkontroluj logs:** `fastmcp logs --tail 200`
2. **Validuj lokálně:** `python -m sukl_mcp`
3. **Otevři issue:** https://github.com/your-org/fastmcp-boilerplate/issues
4. **FastMCP Discord:** https://discord.gg/fastmcp

---

**Poslední aktualizace:** 28. prosince 2024
**FastMCP verze:** 2.14+
**Python verze:** 3.10+
