<!--
  SYNC IMPACT REPORT
  ====================
  Version change: 1.2.0 → 1.3.0
  Modified principles:
    - IV. Build-as-Verification — rewritten to reflect Vitest adoption
      (28 tests, no longer "optional"), `npm test` added as mandatory
    - VI. Data Integrity — updated: build scripts exist (no longer
      "plánováno"), added CI workflow reference
  Modified sections:
    - Technology & Deployment Constraints:
      - Data size corrected: 9.5 MB → 10.4 MB
      - UI components count: 11 → 12
      - MCP rate limiting: "žádný" → 100 req/min (implemented)
      - Demo rate limit: confirmed 10 req/min
    - Repository Structure:
      - Removed docs/plans/ (deleted in cleanup)
      - Added scripts/ directory (build-pharmacies.ts,
        build-reimbursements.ts)
      - Added tests/ directory (api/, lib/)
      - Added .github/workflows/ (3 workflows)
    - Development Workflow:
      - Data automation: "plánována" → implemented (update-data.yml)
      - Added `npm test` as verification step
  Added sections: none
  Removed sections: none
  Templates requiring updates:
    - .specify/templates/plan-template.md — ✅ compatible
    - .specify/templates/spec-template.md — ✅ compatible
    - .specify/templates/tasks-template.md — ✅ compatible
    - .specify/templates/checklist-template.md — ✅ compatible
    - .specify/templates/agent-file-template.md — ✅ compatible
  Follow-up TODOs: none
  Bump rationale: MINOR — Principle IV materially rewritten (testing
  now mandatory), multiple factual corrections across deployment
  constraints and repository structure after Epic 1+2 completion.
  Validation: All claims cross-checked against actual file system.
-->

# SÚKL MCP Server Constitution

## Core Principles

### I. Server-Only Data Layer

Veškerý přístup k farmaceutickým datům probíhá výhradně na serveru.

- `sukl-client.ts` používá `fs.readFileSync` a NESMÍ být nikdy importován
  v klientských komponentách (`"use client"`).
- Data se načítají lazy z `data/bundled-data.json` (10.4 MB) a cachují
  se v paměti procesu. Opakovaný přístup MUSÍ používat sdílený in-memory
  store, nikoliv opakované čtení z disku.
- Fuse.js index se vytváří jednou při prvním přístupu a zůstává
  v paměti po celou dobu životnosti procesu.
- Nová datová pole MUSÍ být přidána do stejného bundled formátu
  nebo jako separátní JSON soubory v `data/`.

**Zdůvodnění:** Serverless runtime na Vercel neumožňuje sdílení stavu
mezi requesty jinak než přes module-level cache. Klientský import by
způsobil build error (fs modul neexistuje v prohlížeči).

### II. Plain TypeScript

Projekt NESMÍ zavádět runtime validační knihovny (Zod, io-ts, Yup)
ani MCP frameworky (xMCP, fastmcp-js).

- Všechny datové typy MUSÍ být definovány jako TypeScript `interface`
  nebo `type` v `src/lib/types.ts`.
- MCP tools jsou implementovány jako plain funkce v `mcp-handler.ts`,
  volající `sukl-client.ts`.
- Vstupní validace se provádí pomocí utility funkcí (`validateString`,
  délkové kontroly) přímo v handler kódu.

**Zdůvodnění:** Projekt je dostatečně malý, aby typová bezpečnost
TypeScriptu stačila. Runtime validace přidává zbytečnou závislost
a zvyšuje bundle size bez měřitelného přínosu.

### III. Czech-First UI

Veškerý uživatelsky viditelný text MUSÍ být v češtině.

- Landing page, demo chat, chybové zprávy v UI — vše česky.
- MCP tool descriptions a error messages v JSON-RPC responses MOHOU
  být v češtině (cílový uživatel je český farmaceut/AI agent).
- Komentáře v kódu, názvy proměnných, commit messages a technická
  dokumentace MOHOU být v angličtině nebo češtině dle kontextu.
- README.md a CLAUDE.md jsou v angličtině (konvence open-source).

**Zdůvodnění:** Primární uživatelská základna je česká. Data pochází
ze SÚKL (Státní ústav pro kontrolu léčiv) a obsahují české texty.

### IV. Build & Test Verification

`npm run build` a `npm test` jsou povinné verifikační metody.

- Každá změna MUSÍ projít `npm run build` před commitem.
  Build provádí TypeScript type-checking a odhalí chyby typů,
  neexistující importy a nekompatibilní API.
- Každá změna MUSÍ projít `npm test` (Vitest, 28 testů: unit +
  integration). Testy pokrývají demo-handler (13), mcp-handler (12)
  a integrační flow (3).
- Selhání testů BLOKUJE merge.
- Linting a formatting tooling NEJSOU konfigurovány. Konzistence
  stylu je zajištěna konvencemi v CLAUDE.md.

**Zdůvodnění:** TypeScript build + Vitest testy společně zajišťují
typovou bezpečnost i funkční korektnost. Test suite ověřuje kritické
cesty MCP protokolu a demo interakcí.

### V. Simplicity (YAGNI)

Každá nová abstrakce, závislost nebo architekturální vrstva MUSÍ
být odůvodněna konkrétní potřebou, nikoliv hypotetickým budoucím
požadavkem.

- NEPOUŽÍVAT design patterns (repository, factory, DI container)
  pokud nejsou vyžadovány minimálně třemi různými konzumenty.
- NEPOUŽÍVAT state management knihovny (Redux, Zustand) —
  React `useState`/`useReducer` stačí.
- Framer-motion komponenty MUSÍ být lazy-loaded přes `next/dynamic`
  aby se nezdržoval initial bundle.
- Každá nová npm závislost MUSÍ být zdůvodněna v commit message.

**Zdůvodnění:** Menší codebase = snazší údržba. Projekt je single-page
aplikace s API endpointy, ne enterprise SaaS.

### VI. Data Integrity

Farmaceutická data MUSÍ pocházet výhradně z oficiálních zdrojů SÚKL.

- Primární zdroj: `opendata.sukl.cz` (CSV soubory, měsíční aktualizace).
- `data/bundled-data.json` MUSÍ být commitnut do repozitáře — je
  vyžadován při build time i runtime na Vercel.
- Data build skripty v `scripts/` (`build-pharmacies.ts`,
  `build-reimbursements.ts`) zpracovávají win-1250 encoding.
- CI workflow `update-data.yml` automaticky aktualizuje data měsíčně
  (28. den měsíce).
- Při aktualizaci dat MUSÍ být zachována zpětná kompatibilita
  formátu bundled JSON (klíče `m`, `a`, `p`, `r`, `_`).

**Zdůvodnění:** Jedná se o zdravotnická data. Nesprávné informace
o léčivech mohou mít reálný dopad na zdraví uživatelů.

### VII. Unified Monolith

Repozitář je jediná Next.js aplikace obsahující tři odlišné
aplikační oblasti sdílející jeden deployment.

- Všechny tři oblasti (MCP server, marketingová landing page,
  interaktivní demo) MUSÍ být deployovány jako jeden celek
  na Vercel z jednoho Next.js buildu.
- Sdílený kód (typy, utility, datová vrstva) žije v `src/lib/`
  a NESMÍ být duplikován mezi oblastmi.
- Každá oblast má vlastní adresář komponent:
  - `src/components/sections/` — 12 landing page sekcí
  - `src/components/demo/` — 10 demo chat komponent
  - `src/app/api/` — 2 API routes (MCP + demo backend)
- `src/components/ui/` obsahuje 12 sdílených UI komponent
  používaných napříč oblastmi.
- Nové oblasti (např. admin panel, dokumentace) MUSÍ být přidány
  jako další sekce/routes v rámci stejné Next.js aplikace,
  nikoliv jako separátní service.

**Zdůvodnění:** Jednotný deployment eliminuje koordinaci mezi
službami. Sdílená datová vrstva (`sukl-client.ts`) zajišťuje
konzistenci a zamezuje duplikaci přístupu k bundled datům.

## Technology & Deployment Constraints

### Runtime & Frameworks

- **Runtime:** Next.js 16.1.6, React 19.2.3, TypeScript 5+
- **Styling:** Tailwind CSS 4 s CSS proměnnými (`--sukl-navy`,
  `--sukl-blue`, `--sukl-light-blue`) definovanými v `globals.css`
- **Search:** Fuse.js 7.1 pro fuzzy matching (in-memory index)
- **Animace:** framer-motion 12 (vždy lazy-loaded přes `next/dynamic`)
- **Testing:** Vitest 4 (28 testů: unit + integration)
- **UI primitiva:** Radix UI (accordion), lucide-react (ikony),
  clsx + tailwind-merge (className utility v `src/lib/utils.ts`)
- **Analytika:** Vercel Analytics + Umami (self-hosted na Railway)
- **Path alias:** `@/*` mapuje na `./src/*` (tsconfig.json)
- **Registry:** `smithery.yaml` pro Smithery MCP registr

### Application Areas

Repozitář obsahuje tři vzájemně propojené aplikační oblasti:

1. **MCP Server** (`src/app/api/mcp/route.ts`, `src/lib/mcp-handler.ts`)
   - JSON-RPC 2.0 over HTTP, 9 nástrojů pro přístup k SÚKL datům
   - CORS wildcard (potřeba pro AI agenty)
   - Rate limit: 100 req/min per IP (in-memory Map)
   - Cílová skupina: AI agenti (Claude, GPT, vlastní integrace)
   - Priorita vývoje: **nejvyšší**

2. **Marketingová Landing Page** (`src/app/page.tsx`,
   `src/components/sections/`)
   - 12 sekcí: Header, Hero, QuickStart, Tools, HowItWorks,
     DemoSection, UseCases, Stats, Why, FAQ, CTA, Footer
   - Navigační kotvy (`#quickstart`, `#tools`, `#demo`, aj.)
   - WCAG skip-link, Particles + Spotlight efekty
   - Cílová skupina: vývojáři, integrátoři, farmaceuti
   - Priorita vývoje: **střední**

3. **Interaktivní Demo** (`src/components/demo/`,
   `src/app/api/demo/route.ts`)
   - Guided tour (3 kroky) + volný chat režim
   - State machine orchestrátor (`useReducer`)
   - localStorage persistuje stav touru (`sukl-tour-complete`,
     `sukl-tour-skipped`)
   - Pattern matching backend (žádné LLM)
   - Rate limit: 10 req/min per IP (in-memory Map)
   - Cílová skupina: potenciální uživatelé k vyzkoušení
   - Priorita vývoje: **nižší**

### Deployment

- **Platforma:** Vercel, region `fra1` (Frankfurt)
- **URL:** `sukl-mcp.vercel.app`
- **Config:** `vercel.json` — rewrites `/mcp` → `/api/mcp`,
  CORS headers pro MCP endpoint
- **MCP protokol:** JSON-RPC 2.0 over HTTP, 9 tools, CORS wildcard
- **Rate limiting:** In-memory Map (resetuje se při cold start);
  MCP API: 100 req/min per IP; Demo API: 10 req/min per IP

### Repository Structure

```
sukl-mcp/
├── package.json                # Dependencies (v5.0.0)
├── vercel.json                 # Deployment config, rewrites, CORS
├── smithery.yaml               # Smithery MCP registry
├── tsconfig.json               # TypeScript config + path aliases
├── next.config.ts              # Next.js configuration
├── vitest.config.ts            # Vitest test configuration
├── CLAUDE.md                   # AI agent runtime guidance
├── data/
│   └── bundled-data.json       # SÚKL data (10.4 MB, committed)
├── scripts/
│   ├── build-pharmacies.ts     # Stažení a zpracování lékáren
│   └── build-reimbursements.ts # Stažení a zpracování úhrad (SCAU)
├── tests/
│   ├── api/                    # Integration testy (MCP flow)
│   └── lib/                    # Unit testy (mcp-handler, demo-handler)
├── .github/workflows/
│   ├── update-data.yml         # Měsíční aktualizace dat (cron 28.)
│   ├── claude.yml              # Claude CI workflow
│   └── claude-code-review.yml  # Claude code review workflow
├── src/
│   ├── app/
│   │   ├── page.tsx            # Landing page (12 sekcí)
│   │   ├── layout.tsx          # Root layout + analytika
│   │   ├── globals.css         # Tailwind + CSS proměnné
│   │   └── api/
│   │       ├── mcp/route.ts    # MCP JSON-RPC endpoint
│   │       └── demo/route.ts   # Demo chat backend
│   ├── components/
│   │   ├── sections/           # 12 landing page sekcí
│   │   ├── demo/               # 10 demo chat komponent
│   │   └── ui/                 # 12 sdílených UI komponent
│   └── lib/
│       ├── types.ts            # TypeScript interfaces (7 typů)
│       ├── sukl-client.ts      # Server-only datová vrstva
│       ├── mcp-handler.ts      # MCP tool implementace (9 tools)
│       ├── demo-handler.ts     # Demo intent parser
│       └── utils.ts            # cn() helper (clsx + twMerge)
└── .specify/
    ├── memory/constitution.md  # Tento soubor
    └── templates/              # Speckit šablony
```

## Development Workflow

- **Verifikace:** `npm run build` a `npm test` před každým commitem.
- **Branching:** Feature branches z `main`, PR pro merge.
- **Commit messages:** Conventional Commits (`feat:`, `fix:`, `chore:`,
  `docs:`, `ci:`, `test:`).
- **Priorita vývoje:** MCP endpoint > Landing page > Demo chat.
- **Data aktualizace:** Automaticky měsíčně (28. den) přes GitHub
  Action (`update-data.yml`). Manuálně: `npx tsx scripts/build-*.ts`.
- **CLAUDE.md:** Slouží jako runtime guidance soubor pro AI agenty.
  MUSÍ být aktualizován při změnách architektury, příkazů nebo
  konvencí.

## Governance

- Tato konstituce nadřazuje všechny ostatní praktiky a konvence.
  V případě konfliktu mezi konstitucí a CLAUDE.md platí konstituce.
- Změny konstituce vyžadují:
  1. Dokumentaci změny (co a proč se mění).
  2. Aktualizaci CLAUDE.md pokud změna ovlivňuje vývojové konvence.
  3. Inkrementaci verze dle sémantického verzování:
     - MAJOR: Odstranění nebo redefinice principu.
     - MINOR: Přidání nového principu nebo sekce.
     - PATCH: Upřesnění formulací, opravy překlepů.
- Compliance review: Každý PR MUSÍ být konzistentní s principy
  této konstituce. Reviewer ověří zejména:
  - Princip I (žádný klientský import serverových modulů)
  - Princip II (žádné nové runtime validační knihovny)
  - Princip IV (build + testy MUSÍ projít)
  - Princip V (zdůvodnění nových závislostí)
  - Princip VI (zdroj dat je SÚKL)
  - Princip VII (sdílený kód v `src/lib/`, žádná duplikace)

**Version**: 1.3.0 | **Ratified**: 2026-02-15 | **Last Amended**: 2026-02-20
