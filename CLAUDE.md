# CLAUDE.md

Tento soubor poskytuje pokyny pro Claude Code (claude.ai/code) při práci s kódem v tomto úložišti.

## Přehled projektu

Jedná se o **dvoujazyčný šablonový MCP server** obsahující:

1. **TypeScript/JavaScript FastMCP šablonu** (kořenový adresář) – původní šablonu pro vytváření MCP serverů
2. **Python SÚKL MCP server** (adresář SUKL-FastMCP/) – komplexní MCP server pro přístup k české farmaceutické databázi (SÚKL)

## Architektura

### TypeScript Boilerplate (kořenový adresář)
- **Vstupní bod**: `src/server.ts` – vytvoří instanci FastMCP serveru
- **Vzor**: Nástroje jsou implementovány jako samostatné funkce (např. `src/add.ts`) a registrovány pomocí `server.addTool()`
- **Validace schématu**: Používá Zod pro validaci parametrů
- **Komponenty serveru**:
  - Nástroje: Funkce dostupné pro AI klienty (např. `add`)
  - Zdroje: Zdroje dat (např. protokoly aplikací)
  - Výzvy: Předkonfigurované šablony výzev (např. git-commit)

### Python SÚKL Server (SUKL-FastMCP/)
- **Architektura**: Vícevrstvý design
  - `client.py`: HTTP klient pro SÚKL REST API a Open Data CSV
  - `models.py`: Pydantic modely pro ověřování dat
  - `server.py`: FastMCP server s více než 7 MCP nástroji
- **Klíčové funkce**:
  - Vyhledávání léků podle názvu, složky nebo ATC kódu
  - Vyhledávání lékáren s filtry
  - Informace o úhradách a dostupnosti
  - Přístup k PIL (příbalové informační letáky)
- **Zdroje dat**:
  - REST API: `prehledy.sukl.cz` (v reálném čase)
  - Open Data: `opendata.sukl.cz` (měsíční aktualizace)

## Vývojové příkazy

### TypeScript/JavaScript
```bash
npm install              # Instalace závislostí
npm run dev             # Spuštění s FastMCP CLI (interaktivní)
npm run start           # Spuštění serveru přímo
npm run build           # Kompilace TypeScriptu
npm run lint            # Kontrola kvality kódu
npm run format          # Automatické formátování kódu
npm run test            # Spuštění testů (zaměření na implementaci nástroje, nikoli na protokol MCP)
```

### Python (server SÚKL)
```bash
# Nastavení virtuálního prostředí
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Instalace závislostí
pip install „fastmcp<3“ httpx pydantic

# Spuštění testovacího skriptu
python test_fastmcp_server.py

# Vývoj v SUKL-FastMCP/sukl-mcp-server/
pip install -e „.[dev]“
pytest tests/ -v
```

## Klíčové vzory

### Přidání nových nástrojů (TypeScript)
1. Vytvořte implementační funkci v samostatném souboru (např. `src/myTool.ts`)
2. Zaregistrujte v `src/server.ts` pomocí `server.addTool()`
3. Definujte parametry pomocí schématu Zod
4. Přidejte test v `src/*.test.ts`

### Přenos serveru FastMCP
- Výchozí: `stdio` (standardní vstup/výstup pro lokální použití)
- Alternativa: Nakonfigurujte pro HTTP/SSE pro vzdálené nasazení.

## CI/CD

Používá semantic-release pro automatické publikování NPM:
- Běží na větvi `main`.
- Vyžaduje tajný klíč `NPM_TOKEN`.
- Oprávnění pracovního postupu: „Čtení a zápis“.
- Konvenční commity spouštějí zvýšení verze.

## Filozofie testování

**Testujte své nástroje, ne protokol MCP**. FastMCP zajišťuje dodržování protokolu – zaměřte testy na obchodní logiku (např. chování funkce `add`, nikoli na obal nástroje MCP).

## Poznámky specifické pro SÚKL

Server SÚKL (`SUKL-FastMCP/`) je implementace připravená pro produkční použití, která demonstruje:
- Komplexní HTTP klient s ukládáním do mezipaměti, omezením rychlosti, logikou opakování
- Parsování CSV ze ZIP archivů (otevřená data)
- Pydantic modely pro typovou bezpečnost
- Více typů nástrojů MCP (vyhledávání, načítání detailů, filtrování)

Slouží jako referenční implementace pro budování datově náročných serverů MCP.

## Použití virtuálního prostředí

Při práci s kódem Python vždy používejte virtuální prostředí umístěné v `venv/`. Aktivujte jej před spuštěním příkazů Python nebo instalací balíčků, abyste se vyhnuli konfliktům balíčků v celém systému.
