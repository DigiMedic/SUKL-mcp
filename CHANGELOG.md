# Changelog

Všechny významné změny v tomto projektu budou dokumentovány v tomto souboru.

Formát vychází z [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
a projekt dodržuje [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2024-12-28

### Added

**Smithery Platform Support:**
- ✅ Docker konfigurace s python:3.10-slim base image
- ✅ `.dockerignore` pro optimalizaci build procesu
- ✅ `smithery.yaml` deployment konfigurace
- ✅ HTTP/Streamable-HTTP transport support
- ✅ Automatická detekce transportu (stdio vs HTTP)
- ✅ Health check endpoint pro monitoring
- ✅ Multi-stage Docker build pro minimální image size
- ✅ Non-root user v Docker kontejneru (security best practice)
- ✅ `SMITHERY_DEPLOYMENT.md` - kompletní deployment guide

**Server Enhancements:**
- ✅ Transport auto-detection via `MCP_TRANSPORT` environment variable
- ✅ Configurable host/port for HTTP transport (`MCP_HOST`, `MCP_PORT`)
- ✅ Dual deployment support - FastMCP Cloud (stdio) + Smithery (HTTP)

**Documentation:**
- ✅ README.md - přidána sekce "Nasazení na Smithery"
- ✅ DEPLOYMENT.md - odkaz na Smithery deployment guide
- ✅ Kompletní Smithery deployment dokumentace

### Changed
- 📦 `server.py` - rozšířená `main()` funkce o transport detection
- 📦 Project podporuje 2 deployment platformy bez úprav kódu

## [2.0.0] - 2024-12-28

### BREAKING CHANGES

**Reorganizace projektu: Z dual-language na Python-only**

- **Odstraněna TypeScript/JavaScript část projektu**
  - Smazány všechny `.ts` soubory z `src/`
  - Odstraněny `package.json`, `tsconfig.json`, `eslint.config.ts`
  - Odstraněny NPM-based GitHub Actions workflows
  - Projekt je nyní čistě Python-based

### Added

**Bezpečnost:**
- ✅ ZIP bomb protection (max 5 GB) v `_extract_zip()`
- ✅ Regex injection prevention (`regex=False` v pandas `str.contains()`)
- ✅ Kompletní input validace:
  - `search_medicines`: query délka (max 200), limit range (1-100)
  - `get_medicine_detail`: SÚKL kód validace (číselný, max 7 znaků)
  - `get_atc_groups`: ATC prefix validace (max 7 znaků)
- ✅ Custom exception types (`SUKLException`, `SUKLValidationError`, `SUKLZipBombError`, `SUKLDataError`)

**Performance:**
- ✅ Async I/O pro ZIP extraction (přes `loop.run_in_executor()`)
- ✅ Paralelní CSV loading (5 souborů současně přes `asyncio.gather()`)
- ✅ Race condition fix v `get_sukl_client()` (double-checked locking s `asyncio.Lock`)

**Konfigurace:**
- ✅ Environment variables podpora:
  - `SUKL_OPENDATA_URL` - URL pro Open Data ZIP
  - `SUKL_CACHE_DIR` - cache adresář (default: `/tmp/sukl_dlp_cache`)
  - `SUKL_DATA_DIR` - data adresář (default: `/tmp/sukl_dlp_data`)
  - `SUKL_DOWNLOAD_TIMEOUT` - download timeout (default: 120s)

**Dependencies:**
- ✅ `pandas>=2.0.0` přidáno do core dependencies

**FastMCP Cloud Support:**
- ✅ `fastmcp.yaml` - konfigurace pro cloud deployment
- ✅ `__main__.py` - entry point pro `python -m sukl_mcp`
- ✅ Absolutní importy - fix pro "attempted relative import" chybu v cloud
- ✅ `DEPLOYMENT.md` - kompletní guide pro FastMCP Cloud nasazení

**Dokumentace:**
- ✅ README.md kompletně přepsána pro Python-only projekt
- ✅ CLAUDE.md aktualizována - Python best practices, bezpečnostní vzory
- ✅ Přidány code examples pro async I/O, validaci, thread-safe patterns

### Fixed

- 🔧 **Race condition** v globální SÚKL klient instanci (paralelní `initialize()` calls)
- 🔧 **Blocking I/O** v ZIP extraction (blokoval event loop)
- 🔧 **Blocking I/O** v CSV loading (sekvenční načítání 5 souborů)
- 🔧 **Regex injection** v search query (user input jako regex pattern)
- 🔧 **Missing validation** - žádné kontroly vstupních hodnot
- 🔧 **Missing pandas dependency** - runtime ImportError při prvním spuštění
- 🔧 **Hardcoded paths** - `/tmp` nemožné změnit bez editace kódu

### Changed

- 📦 Minimální Python verze: `>=3.10`
- 📦 FastMCP verze: `>=2.14.0,<3.0.0`
- 📦 Projekt struktura:
  ```
  sukl_mcp/
  ├── src/sukl_mcp/
  │   ├── server.py
  │   ├── client_csv.py    (hlavní změny zde)
  │   ├── models.py
  │   ├── exceptions.py    (NEW)
  │   └── __init__.py
  ├── tests/
  └── pyproject.toml
  ```

### Removed

- ❌ TypeScript boilerplate (`src/server.ts`, `src/add.ts`)
- ❌ Node.js konfigurace (`package.json`, `tsconfig.json`)
- ❌ NPM workflows (`.github/workflows/main.yaml`, `.github/workflows/feature.yaml`)
- ❌ Veškeré Node.js/TypeScript dependencies

## [1.0.0] - 2024-12-23

### Added

- ✨ Iniciální release SÚKL MCP serveru
- ✨ 7 MCP tools pro farmaceutická data
- ✨ CSV-based data loading z SÚKL Open Data
- ✨ Podpora pro 68,248 léčivých přípravků
- ✨ TypeScript boilerplate jako doprovodný příklad

---

## Migration Guide: 1.x → 2.0

### Pro vývojáře

**1. Aktualizace závislostí:**
```bash
pip install -e ".[dev]"  # pandas bude automaticky nainstalován
```

**2. Environment variables (volitelné):**
```bash
export SUKL_CACHE_DIR=/var/cache/sukl
export SUKL_DATA_DIR=/var/lib/sukl
export SUKL_DOWNLOAD_TIMEOUT=180.0
```

**3. Error handling:**
```python
from sukl_mcp.exceptions import SUKLValidationError, SUKLZipBombError

try:
    results = await client.search_medicines("")
except SUKLValidationError as e:
    print(f"Neplatný vstup: {e}")
```

### Pro uživatele TypeScript boilerplate

TypeScript část projektu byla odstraněna. Pokud jste ji používali:

1. **Alternativy:**
   - Oficiální FastMCP TypeScript template: https://github.com/gofastmcp/fastmcp-template-typescript
   - Tento projekt je nyní čistě Python SÚKL server

2. **Data pro AI agenty zůstávají stejná:**
   - MCP protocol je stejný
   - SÚKL server funguje identicky
   - Pouze infrastruktura (jazyk) se změnila

### Breaking Changes Summary

| Změna | Verze 1.x | Verze 2.0 |
|-------|----------|----------|
| Jazyk | TypeScript + Python | Python only |
| Package manager | npm + pip | pip only |
| Struktura | dual-project | single-project |
| TypeScript files | ✅ | ❌ |
| pandas dependency | ❌ (chyběla) | ✅ |
| Input validation | ❌ | ✅ |
| Async I/O | ❌ (blocking) | ✅ (non-blocking) |
| ENV config | ❌ | ✅ |
| ZIP bomb protection | ❌ | ✅ |
| Custom exceptions | ❌ | ✅ |

---

**Data source:** SÚKL Open Data (https://opendata.sukl.cz)
**Aktualizace dat:** 23. prosince 2024
**License:** MIT
