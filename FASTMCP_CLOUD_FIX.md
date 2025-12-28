# FastMCP Cloud Deployment - Fixed Issues

## 🐛 Problém

Při nasazení na FastMCP Cloud se objevovala chyba:

```
[12/28/25 18:39:36] ERROR    Failed to run: attempted relative import
                             with no known parent package
```

## ✅ Řešení

### 1. Změna importů z relativních na absolutní

**Před (nefungovalo v cloud):**
```python
# server.py
from .client_csv import get_sukl_client
from .models import MedicineSearchResult

# client_csv.py
from .exceptions import SUKLValidationError
```

**Po (funguje v cloud):**
```python
# server.py
from sukl_mcp.client_csv import get_sukl_client
from sukl_mcp.models import MedicineSearchResult

# client_csv.py
from sukl_mcp.exceptions import SUKLValidationError
```

### 2. Vytvoření fastmcp.yaml

Nový konfigurační soubor pro FastMCP Cloud:

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

### 3. Přidání __main__.py

Entry point pro spuštění serveru:

```python
# src/sukl_mcp/__main__.py
if __name__ == "__main__":
    from sukl_mcp.server import mcp
    mcp.run()
```

## 📝 Změněné soubory

1. **`src/sukl_mcp/server.py`**
   - Změna: Relativní → absolutní importy
   - Změna: Version 1.0.0 → 2.0.0

2. **`src/sukl_mcp/client_csv.py`**
   - Změna: Relativní → absolutní import pro exceptions

3. **`fastmcp.yaml`** (NOVÝ)
   - Konfigurace pro FastMCP Cloud deployment

4. **`src/sukl_mcp/__main__.py`** (NOVÝ)
   - Entry point pro `python -m sukl_mcp`

5. **`DEPLOYMENT.md`** (NOVÝ)
   - Kompletní guide pro nasazení na cloud

## ✅ Validace

Všechny importy nyní fungují:

```bash
$ python -c "from sukl_mcp.server import mcp; print(mcp.version)"
2.0.0

$ python -c "from sukl_mcp import SUKLClient; print('OK')"
OK
```

## 🚀 Deployment

```bash
fastmcp deploy
```

Server nyní úspěšně běží na FastMCP Cloud bez chyby "attempted relative import".

## 📚 Dokumentace

- **DEPLOYMENT.md** - Detailní deployment guide
- **README.md** - Přidána sekce "Nasazení na FastMCP Cloud"
- **CHANGELOG.md** - Dokumentovány změny v2.0.0

## 🔍 Proč to nefungovalo?

FastMCP Cloud spouští server jako standalone modul, ne jako součást balíčku. Relativní importy (`from .module import ...`) fungují pouze když je Python schopen najít parent package. V cloud prostředí to není zaručeno.

**Absolutní importy** (`from sukl_mcp.module import ...`) fungují vždy, protože Python hledá `sukl_mcp` v `sys.path`, což je garantováno.

## ⚠️ Důležité poznámky

1. **`__init__.py` může mít relativní importy** - je to package initialization, funguje to.
2. **Ostatní moduly MUSÍ mít absolutní importy** - server.py, client_csv.py, atd.
3. **Testuj lokálně** před deploymentem: `python -c "from sukl_mcp.server import mcp"`

---

**Fixed:** 28. prosince 2024
**Version:** 2.0.0
**Status:** ✅ Deployed and working on FastMCP Cloud
