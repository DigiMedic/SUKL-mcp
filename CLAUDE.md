# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SUKL MCP Server — Next.js 16 application providing AI agents access to the Czech SUKL pharmaceutical database (~68k medicines) via MCP protocol. Single deployment: landing page + MCP Streamable HTTP endpoint + interactive guided demo.

**Live URL:** https://sukl-mcp.vercel.app
**MCP endpoint:** https://sukl-mcp.vercel.app/mcp

## Commands

```bash
npm install        # Install dependencies
npm run dev        # Dev server (http://localhost:3000)
npm run build      # Production build (also runs TypeScript check)
npm start          # Start production server
npm test           # Run all Vitest tests (28 tests)
npm run test:watch # Vitest watch mode
npm run analyze    # Bundle size analysis (opens browser)
```

Run a single test file: `npx vitest run tests/lib/mcp-handler.test.ts`
Run tests matching a name: `npx vitest run -t "search-medicine"`

Tests: 28 total (13 demo-handler, 12 mcp-handler, 3 integration). Config in `vitest.config.ts`, test files in `tests/`.

## Architecture

### Three entry points in one Next.js app

1. **Landing page** (`src/app/page.tsx`) — Client-side `"use client"` page composing 12 section components. Section order matters for scroll navigation anchors (`#quickstart`, `#tools`, `#demo`, etc.).

2. **MCP endpoint** (`src/app/api/mcp/route.ts`) — JSON-RPC 2.0 over HTTP. Delegates to `src/lib/mcp-handler.ts` which implements 9 tools. Supports batch requests. CORS wildcard enabled via `vercel.json` headers + OPTIONS handler. URL rewrite: `/mcp` -> `/api/mcp`. Rate limit: 100 req/min per IP.

3. **Demo API** (`src/app/api/demo/route.ts`) — Backend for the interactive demo chat. Uses regex/pattern matching (no LLM). Rate limited: 10 req/min per IP via in-memory Map.

### Data flow

```
bundled-data.json (10.4 MB, committed)
        | fs.readFileSync (lazy, cached in memory)
    sukl-client.ts (Fuse.js fuzzy search index)
       /        \
mcp-handler.ts    demo-handler.ts -> demo/route.ts
       |
  api/mcp/route.ts
```

**Critical:** `sukl-client.ts` uses `fs.readFileSync` — it is server-only. Never import it in client components.

### Demo: Guided Tour system

The demo section uses a state machine orchestrator pattern:

- `guided-tour.tsx` — `useReducer` state machine: `intro -> step-1 -> step-2 -> step-3 -> complete -> free`
- Steps chain data: step 1 search returns SUKL code -> step 2 uses it for detail -> step 2 returns ATC -> step 3 uses it
- `chat-widget.tsx` supports two modes via `mode` prop: `"guided"` (single suggested query) and `"free"` (enriched example chips)
- `localStorage` keys `sukl-tour-complete` / `sukl-tour-skipped` skip tour for returning visitors
- `GuidedTour` is lazy-loaded via `next/dynamic` in `demo-section.tsx` to defer framer-motion bundle

### Component layers

- `src/components/sections/` — Landing page sections (stateless, visual)
- `src/components/demo/` — Demo chat system (guided tour + chat widget + message rendering)
- `src/components/ui/` — Reusable animated components (shimmer-button, particles, typing-animation, etc.)

## Coding Conventions

- **No Zod** — Plain TypeScript interfaces in `src/lib/types.ts`
- **No xMCP framework** — MCP tools are plain functions in `mcp-handler.ts` calling `sukl-client.ts`
- **Czech UI text** — All user-facing strings must be in Czech
- **Tailwind CSS 4** — Theming via CSS variables (`--sukl-navy`, `--sukl-blue`, `--sukl-light-blue`) defined in `globals.css`
- **framer-motion** — Used for animations; wrap heavy animated components with `next/dynamic`
- **`@/*` path alias** — Maps to `./src/*` (configured in `tsconfig.json`)

## Data & SUKL APIs

- **Bundled data** (`data/bundled-data.json`, 10.4 MB) — 68k medicines, 2662 pharmacies, 8480 reimbursements, 6907 ATC codes. Must be committed (needed at build time on Vercel).
- **Build scripts** (`scripts/build-pharmacies.ts`, `scripts/build-reimbursements.ts`) — download and process data from SUKL. Handle WIN-1250 encoding.
- **CI automation** (`.github/workflows/update-data.yml`) — monthly cron on 28th day updates bundled data.
- **Document API** — PIL/SPC tools return download URLs from `https://prehledy.sukl.cz/dlp/v1/dokumenty-metadata/{kodSukl}`. PDF parsing via docling-mcp companion.

## Deployment

- **Platform:** Vercel, region `fra1` (Frankfurt)
- **Config:** `vercel.json` — rewrites `/mcp` to `/api/mcp`, CORS headers for MCP endpoint
- **Security headers:** CSP, X-Frame-Options, X-Content-Type-Options configured in `next.config.ts`

## Known Constraints

- PIL/SPC returns download URL from SUKL API (prehledy.sukl.cz) — PDF parsing via docling-mcp companion
- In-memory rate limiting resets on serverless cold start
- Cold start may be slow due to 10.4 MB JSON lazy-loading
