# SUKL MCP Server - Instrukce pro kódování s AI

## Přehled projektu

SUKL MCP Server je **Next.js 16** aplikace poskytující AI agentům přístup k databázi Státního ústavu pro kontrolu léčiv (SÚKL) přes **Model Context Protocol**. Zpracovává ~68 tisíc léčivých přípravků pomocí **Fuse.js** pro fuzzy vyhledávání v paměti.

Jeden deployment obsahuje tři funkce:
- **Landing page** — 12 sekcí s interaktivním demo
- **MCP endpoint** — JSON-RPC 2.0 na `/mcp` (9 nástrojů)
- **Demo chat** — regex/pattern matching bez LLM

**Live URL:** https://sukl-mcp.vercel.app
**MCP endpoint:** https://sukl-mcp.vercel.app/mcp

## Architektura a hlavní komponenty

### 1. Datová vrstva (`src/lib/sukl-client.ts`)
- **Server-only** modul — používá `fs.readFileSync` pro lazy-loading `data/bundled-data.json` (10.4 MB).
- **Fuse.js** index pro fuzzy vyhledávání přes 68k+ záznamů.
- Data: 68 248 léčiv, 6 907 ATC kódů, 2 662 lékáren, 8 480 záznamů o úhradách.
- **Nikdy neimportovat v klientských komponentách.**

### 2. MCP vrstva (`src/lib/mcp-handler.ts`)
- JSON-RPC 2.0 handler implementující 9 MCP nástrojů.
- Volá funkce z `sukl-client.ts`.
- Rate limiting: 100 req/min per IP (in-memory).

### 3. Demo vrstva (`src/lib/demo-handler.ts`)
- Regex/pattern matching intent parser pro demo chat.
- Rate limiting: 10 req/min per IP.
- Guided Tour: 3-krokový onboarding (hledání → detail → ATC).

### 4. API Routes
- `src/app/api/mcp/route.ts` — MCP Streamable HTTP endpoint
- `src/app/api/demo/route.ts` — Demo chat backend

### 5. Typy (`src/lib/types.ts`)
- Plain **TypeScript interfaces** — bez Zod, bez Pydantic.
- Všechny datové struktury na jednom místě.

## Vývojový proces

```bash
npm install       # Instalace závislostí
npm run dev       # Dev server (http://localhost:3000)
npm run build     # Produkční build (vč. TypeScript check)
npm start         # Spustit produkční server
npm test          # Vitest (28 testů: unit + integration)
npm run test:watch # Vitest watch mode
npm run analyze   # Analýza velikosti bundlu
```

## Konvence kódování

- **Framework**: Next.js 16 (App Router, React 19, Turbopack)
- **TypeScript 5**: Strict mode, plain interfaces (bez Zod)
- **Tailwind CSS 4**: Custom theme s CSS proměnnými (`--sukl-navy`, `--sukl-blue`, `--sukl-light-blue`) v `globals.css`
- **Framer Motion**: Animace na landing page, obalit těžké komponenty s `next/dynamic`
- **Path alias**: `@/*` → `./src/*`
- **Jazyk UI**: Veškerý uživatelský text v **češtině**

## Testovací vzory

- **Framework**: Vitest 4 (ne pytest)
- **Umístění**: `tests/` adresář, konfigurace v `vitest.config.ts`
- **Testy**: 28 celkem (13 demo-handler, 12 mcp-handler, 3 integration)
- **Spuštění**: `npm test` nebo `npm run test:watch`

## Klíčové detaily implementace

- **Data**: `bundled-data.json` musí být commitnutý (potřeba při buildu na Vercel)
- **PIL/SPC**: Vrací URL ke stažení PDF z SÚKL API (`prehledy.sukl.cz/dlp/v1/`), ne parsovaný obsah
- **Docling-mcp**: Doporučený companion MCP server pro parsování PDF dokumentů
- **Rate limiting**: In-memory Map, resetuje se při serverless cold start
- **Deployment**: Vercel, region `fra1` (Frankfurt), CORS wildcard pro MCP endpoint
