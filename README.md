> **Lokální kandidát v6.0.0 — veřejný plugin pro ChatGPT.** Nové publikační rozhraní je `/chatgpt/mcp`; původní `/mcp` má opravený SDK transport. Návod, změny kontraktu a zbývající publikační kroky jsou v [docs/openai-publication.md](docs/openai-publication.md). Veřejný plugin ještě není nasazen ani publikován. Níže uvedené starší materiály popisují původní v5; při rozporu platí nový návod.

# SUKL MCP Server

**MCP server pro českou databázi léčivých přípravků SÚKL** — landing page, MCP endpoint a interaktivní demo chat v jednom Next.js 16 projektu.

[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-blue.svg)](https://www.typescriptlang.org/)
[![MCP Protocol](https://img.shields.io/badge/MCP-2025--03--26-green.svg)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-28%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Konsolidovaná aplikace: landing page + MCP Streamable HTTP endpoint + demo chat na jedné URL.

---

## O projektu

SUKL MCP Server implementuje [Model Context Protocol](https://modelcontextprotocol.io/) a poskytuje AI agentům (Claude, GPT-4, atd.) přístup k databázi **68 000+ léčivých přípravků** registrovaných v České republice.

### Hlavní funkce

- **9 MCP tools** pro komplexní práci s farmaceutickými daty
- **Fuzzy vyhledávání** pomocí Fuse.js s tolerancí překlepů
- **Landing page** s 13 sekcemi a interaktivním demo
- **Pricing** — 3 cenové úrovně (Free/Pro/Enterprise) s registračními formuláři
- **Lead capture** — formuláře pro registraci, enterprise kontakt a newsletter → Notion CRM + Resend email notifikace
- **Guided demo onboarding** — 3-krokový interaktivní tour (hledání → detail → ATC)
- **MCP Streamable HTTP** endpoint (JSON-RPC 2.0) na `/mcp`
- **Demo chat** bez LLM — regex/pattern matching pro ukázku tool calls
- **GDPR souhlas** — povinný checkbox ve všech formulářích s timestampem
- **Analytics** — Vercel Analytics + Umami tracking konverzního funnelu
- **Dark/Light mode** s plně responzivním designem
- **Automatická aktualizace dat** — CI workflow (měsíční cron)

---

## Quick Start

### Připojení MCP serveru ke Claude

Pro okamžité použití bez instalace:

```json
{
  "mcpServers": {
    "sukl": {
      "type": "url",
      "url": "https://sukl-mcp.vercel.app/mcp"
    }
  }
}
```

### Lokální vývoj

```bash
# 1. Klonovat repozitář
git clone https://github.com/petrsovadina/SUKL-mcp.git
cd SUKL-mcp

# 2. Instalovat závislosti
npm install

# 3. Nastavit env proměnné (volitelné — pro lead capture formuláře)
cp .env.example .env.local
# Vyplnit NOTION_API_KEY a databázové ID

# 4. Spustit dev server
npm run dev

# 5. Otevřít http://localhost:3000
```

> **Poznámka:** Landing page a MCP endpoint fungují bez env proměnných. Notion integrace (formuláře) vyžaduje `NOTION_API_KEY` a databázové ID.

### Build & Testy

```bash
npm run build      # Produkční build (vč. TypeScript check)
npm start          # Spustit produkční server
npm test           # Vitest (28 testů: unit + integration)
npm run test:watch # Vitest watch mode
npm run analyze    # Analýza velikosti bundlu
```

---

## MCP Tools (9)

| # | Tool | Popis |
|---|------|-------|
| 1 | `search-medicine` | Fuzzy vyhledávání léčiv podle názvu, účinné látky nebo SUKL kódu |
| 2 | `get-medicine-details` | Detail léčivého přípravku podle SUKL kódu |
| 3 | `check-availability` | Kontrola dostupnosti na trhu |
| 4 | `find-pharmacies` | Vyhledání lékáren podle města, PSČ nebo 24h provozu |
| 5 | `get-atc-info` | ATC klasifikace léčiv |
| 6 | `get-reimbursement` | Informace o úhradách, cenách a doplatcích |
| 7 | `get-pil-content` | Příbalový leták (PIL) — vrací URL ke stažení z SÚKL API |
| 8 | `get-spc-content` | Souhrn údajů o přípravku (SPC) — vrací URL ke stažení z SÚKL API |
| 9 | `batch-check-availability` | Hromadná kontrola dostupnosti (max 50 léků) |

### Příklady použití

```bash
# Test MCP endpointu - initialize
curl -X POST https://sukl-mcp.vercel.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Seznam nástrojů
curl -X POST https://sukl-mcp.vercel.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# Vyhledání léku
curl -X POST https://sukl-mcp.vercel.app/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search-medicine","arguments":{"query":"ibuprofen","limit":5}}}'
```

---

## Architektura

```
SUKL-mcp/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Landing page (13 sekcí)
│   │   ├── layout.tsx            # Root layout (fonty, metadata, theme)
│   │   ├── globals.css           # Tailwind 4 + SUKL CSS proměnné
│   │   └── api/
│   │       ├── mcp/route.ts      # MCP Streamable HTTP (JSON-RPC 2.0)
│   │       ├── demo/route.ts     # Demo chat backend (rate limited)
│   │       ├── register/route.ts # Pro registrace → Notion Leads DB
│   │       ├── contact/route.ts  # Enterprise kontakt → Notion Enterprise DB
│   │       └── newsletter/route.ts # Newsletter → Notion Newsletter DB
│   ├── components/
│   │   ├── sections/             # 13 landing page sekcí (vč. pricing)
│   │   ├── forms/                # Modální formuláře (register, contact)
│   │   ├── demo/                 # Guided tour + chat widget (10 komponent)
│   │   ├── icons/                # SVG ikony
│   │   ├── ui/                   # 12 reusable UI komponent
│   │   ├── theme-provider.tsx    # next-themes provider
│   │   └── theme-toggle.tsx      # Přepínač dark/light mode
│   └── lib/
│       ├── sukl-client.ts        # Data layer (Fuse.js, lazy-loaded JSON)
│       ├── types.ts              # TypeScript interfaces
│       ├── mcp-handler.ts        # JSON-RPC handler (9 tools)
│       ├── demo-handler.ts       # Intent parser (regex)
│       ├── notion.ts             # Notion CRM client (leads, enterprise, newsletter)
│       ├── resend.ts             # Resend email client (potvrzení registrace, enterprise notifikace)
│       ├── analytics.ts          # Event tracking (Vercel Analytics + Umami)
│       └── utils.ts              # cn() helper
├── data/
│   └── bundled-data.json         # 10.4 MB (68k léků, 2662 lékáren, 8480 úhrad, 6907 ATC)
├── docs/
│   ├── api-reference.md          # API reference (specifikace 9 tools)
│   └── architecture.md           # Architektura s Mermaid diagramy
├── scripts/
│   ├── build-pharmacies.ts       # Stažení a zpracování dat lékáren
│   └── build-reimbursements.ts   # Stažení a zpracování dat úhrad (SCAU)
├── tests/                        # Vitest testy (28)
├── .github/workflows/
│   ├── update-data.yml           # Měsíční aktualizace dat z SÚKL
│   ├── claude.yml                # Claude CI workflow
│   └── claude-code-review.yml    # Claude code review
├── vercel.json                   # Deployment config + CORS
└── smithery.yaml                 # MCP registry
```

### Technologie

- **Next.js 16.1.6** — App Router, React 19.2.3, Turbopack
- **TypeScript 5** — Strict mode, plain interfaces (bez Zod)
- **Tailwind CSS 4** — Custom theme s CSS proměnnými (dark/light)
- **Fuse.js 7.1** — Fuzzy search přes 68k+ záznamů
- **Framer Motion 12** — Animace na landing page (lazy-loaded)
- **next-themes** — Dark/light mode
- **Radix UI** — Accordion, **lucide-react** — ikony
- **@notionhq/client** — CRM backend pro lead capture formuláře
- **Resend** — Transakční emaily (potvrzení registrace, enterprise notifikace)
- **@vercel/analytics** — Konverzní tracking
- **Vitest 4** — Unit a integrační testy (28)
- **Vercel** — Deployment (region `fra1`)

### Data

Aplikace používá bundled JSON soubor (`data/bundled-data.json`, 10.4 MB) obsahující:

- **68 248** léčivých přípravků z SÚKL
- **6 907** ATC klasifikačních kódů
- **2 662** lékáren
- **8 480** záznamů o úhradách a cenách

Data jsou lazy-loaded při prvním požadavku a cachována v paměti. Automatická měsíční aktualizace přes GitHub Actions workflow (28. den v měsíci). Manuální aktualizace: `npx tsx scripts/build-pharmacies.ts` a `npx tsx scripts/build-reimbursements.ts`.

### PIL/SPC dokumenty

Nástroje `get-pil-content` a `get-spc-content` vracejí URL ke stažení PDF dokumentů z SÚKL API (`prehledy.sukl.cz`). Pro parsování obsahu PDF doporučujeme použít [docling-mcp](https://github.com/docling-project/docling) jako companion MCP server.

---

## Prostředí (Environment Variables)

| Proměnná | Popis | Povinná |
|----------|-------|---------|
| `NOTION_API_KEY` | Notion integration token | Pro formuláře |
| `NOTION_DB_LEADS` | DB ID pro Pro registrace | Pro formuláře |
| `NOTION_DB_ENTERPRISE` | DB ID pro Enterprise kontakty | Pro formuláře |
| `NOTION_DB_NEWSLETTER` | DB ID pro newsletter odběratele | Pro formuláře |
| `RESEND_API_KEY` | Resend API klíč | Pro emaily |
| `RESEND_FROM_EMAIL` | Ověřená odesílací adresa | Pro emaily |
| `RESEND_OWNER_EMAIL` | Email pro enterprise notifikace | Pro emaily |

Viz `.env.example` pro šablonu. Notion integrace vyžaduje sdílení všech 3 databází s integrací. Resend emaily jsou volitelné — formuláře fungují i bez nich.

---

## Deployment

Projekt je nasazený na Vercel:

- **URL:** https://sukl-mcp.vercel.app
- **MCP endpoint:** https://sukl-mcp.vercel.app/mcp
- **Region:** Frankfurt (fra1)

### Vercel konfigurace

- Framework: Next.js (automatická detekce)
- Root directory: `.`
- Build command: `next build`
- `/mcp` → rewrite na `/api/mcp`
- CORS headers pro MCP endpoint (Access-Control-Allow-Origin: *)
- Environment variables: `NOTION_API_KEY`, `NOTION_DB_*`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_OWNER_EMAIL`

---

## Známá omezení

- **PIL/SPC vrací URL** — nástroje vrací odkaz na PDF ke stažení z SÚKL API, ne parsovaný obsah. Pro extrakci textu z PDF použijte docling-mcp.
- **Cold start** — první požadavek na Vercel může být pomalejší kvůli lazy-loading 10.4 MB JSON
- **In-memory rate limiting** — reset při serverless cold start (100 req/min MCP, 10 req/min demo)

---

## Právní upozornění

Tento server poskytuje informace výhradně pro informační účely. Data mohou být zpožděná a neměla by nahrazovat konzultaci s lékařem nebo lékárníkem. Oficiální a právně závazné informace naleznete na https://www.sukl.cz.

---

## Contributing

```bash
# Fork a klonovat repozitář
git clone https://github.com/<your-username>/SUKL-mcp.git
cd SUKL-mcp
npm install
npm test          # Ověřit, že testy procházejí
npm run dev       # Spustit dev server
```

Pull requesty jsou vítány. Pro větší změny nejdříve otevřete issue k diskuzi.

---

## License

MIT License — viz [LICENSE](LICENSE). Copyright 2025-2026 Petr Sovadina.

Data poskytnutá SÚKL pod podmínkami Open Data: https://opendata.sukl.cz/?q=podminky-uziti

---

**Vytvořeno s [Next.js](https://nextjs.org)** | **Data od [SÚKL](https://www.sukl.cz)** | **Protokol [MCP](https://modelcontextprotocol.io)**
