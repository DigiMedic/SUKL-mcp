# SUKL MCP Server - Instrukce pro kódování s AI

## Přehled projektu
Toto je produkční **FastMCP** server poskytující AI agentům přístup k databázi Státního ústavu pro kontrolu léčiv (SÚKL). Zpracovává ~68 tisíc léčivých přípravků pomocí knihovny **pandas** pro vyhledávání v paměti a **asyncio** pro souběžnost.

## Architektura a hlavní komponenty

### 1. Datová vrstva (`src/sukl_mcp/client_csv.py`)
- **`SUKLDataLoader`**: Zajišťuje asynchronní stahování a extrakci ZIP souborů z Open Dat SÚKL.
  - *Bezpečnost*: Implementuje ochranu proti ZIP bombám (max. 5 GB extrahovaných dat).
  - *Úložiště*: Ukládá data do mezipaměti v `/tmp/sukl_dlp_cache`.
- **`SUKLClient`**: Thread-safe singleton spravující pandas DataFramy.
  - *Vzor*: Double-checked locking pro inicializaci.
  - *Vyhledávání*: Víceúrovňová pipeline (Látka -> Přesný název -> Podřetězec -> Fuzzy).

### 2. API vrstva (`src/sukl_mcp/server.py`)
- Postaveno na **FastMCP** (FastAPI + Pydantic).
- Nástroje registrované pomocí `@mcp.tool`.
- Správa životního cyklu pomocí `@asynccontextmanager` pro obsluhu spuštění a ukončení klienta.

### 3. Modely (`src/sukl_mcp/models.py`)
- Modely **Pydantic v2** pro všechny datové struktury.
- Používejte `Field(..., description="...")` pro poskytnutí kontextu LLM modelům využívajícím tyto nástroje.
- Enumy pro pevné sady hodnot jako `RegistrationStatus` nebo `AvailabilityStatus`.

## Vývojový proces

Pro standardní úkoly vždy používejte **Makefile**:

- **Nastavení**: `make install` (instalace včetně vývojových závislostí)
- **Spuštění**: `make run` (spustí server v režimu stdio)
- **Testování**: `make test` (spustí pytest) nebo `make test-cov` (report pokrytí)
- **Linting**: `make lint` (spustí `ruff check` a `mypy`)
- **Formátování**: `make format` (spustí `black`)
- **Kompletní kontrola**: `make dev` (spustí formátování, testy a linting)

## Konvence kódování

- **Styl**: Přísné dodržování formátování **Black** a lintingu **Ruff**.
- **Typování**: Vyžadováno 100% pokrytí typy. K ověření použijte `mypy`.
- **Async**: Používejte `async/await` pro všechny I/O operace (čtení souborů, HTTP požadavky).
- **Zpracování chyb**:
  - Používejte vlastní výjimky z `src/sukl_mcp/exceptions.py` (např. `SUKLValidationError`).
  - Nikdy neposkytujte surové interní chyby MCP klientovi.
- **Dokumentace**:
  - Docstringy v **češtině** pro popisy určené uživatelům (instrukce pro MCP nástroje).
  - Interní komentáře v kódu mohou být v angličtině nebo češtině (udržujte konzistenci).

## Testovací vzory

- **Framework**: `pytest` s `pytest-asyncio`.
- **Umístění**: Všechny testy v `tests/`.
- **Mockování**: V testech mockujte externí HTTP volání (SÚKL API) a souborové I/O.
- **Validace**: Testujte hraniční případy (prázdné dotazy, dlouhé řetězce, neplatné vstupy), jak je vidět v `tests/test_validation.py`.

## Klíčové detaily implementace

- **Pandas**: Kde je to možné, používejte vektorizované operace. Vyhněte se iterování přes řádky.
- **Bezpečnost**:
  - V operacích s řetězci v pandas nastavte `regex=False`, abyste zabránili ReDoS útokům.
  - Validujte všechny vstupy pomocí `SUKLValidationError`.
- **Fuzzy vyhledávání**: Používá `rapidfuzz` s konfigurovatelným prahem (výchozí hodnota 80).
