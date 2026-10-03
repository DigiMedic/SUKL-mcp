# CLAUDE.md

Current local release candidate: application v6.0.0, public ChatGPT plugin v1.0.0. Read `docs/openai-publication.md` for current endpoint contracts, build commands and release gates. The legacy context below describes v5 where it differs.

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

Manual data update: `npx tsx scripts/build-pharmacies.ts` and `npx tsx scripts/build-reimbursements.ts` (downloads from SUKL, handles WIN-1250 encoding).

Tests: 36 total (13 demo-handler, 12 mcp-handler, 8 newsletter-route, 3 integration). Config in `vitest.config.ts`, test files in `tests/`.

## Architecture

### Entry points

1. **Landing page** (`src/app/page.tsx`) — Client-side `"use client"` page composing 13 section components. Section order matters for scroll navigation anchors (`#quickstart`, `#tools`, `#demo`, `#pricing`, etc.).

2. **MCP endpoint** (`src/app/api/mcp/route.ts`) — JSON-RPC 2.0 over HTTP. Delegates to `src/lib/mcp-handler.ts` which implements 9 tools. Supports batch requests. CORS wildcard enabled via `vercel.json` headers + OPTIONS handler. URL rewrite: `/mcp` -> `/api/mcp`. Rate limit: 100 req/min per IP.

3. **Demo API** (`src/app/api/demo/route.ts`) — Backend for the interactive demo chat. Uses regex/pattern matching (no LLM). Rate limited: 10 req/min per IP via in-memory Map.

4. **Lead capture APIs** — Three form submission endpoints, all rate limited (5 req/min per IP):
   - `src/app/api/register/route.ts` — Pro tier registration → Notion "Leads" DB + Resend confirmation email
   - `src/app/api/contact/route.ts` — Enterprise contact form → Notion "Enterprise" DB + Resend notification email
   - `src/app/api/newsletter/route.ts` — Newsletter signup → Notion "Newsletter" DB + Resend confirmation email + duplicate detection
   - All use `src/lib/notion.ts` (Notion CRM) and `src/lib/resend.ts` (email notifications)
   - Resend email failures are non-blocking (caught silently) — form submission succeeds even if email fails

### Data flow

```
bundled-data.json (10.4 MB, committed)
        | fs.readFileSync (lazy, cached in memory)
    sukl-client.ts (Fuse.js fuzzy search index, 1-hour cache TTL)
       /        \
mcp-handler.ts    demo-handler.ts -> demo/route.ts
       |
  api/mcp/route.ts
```

**Critical:** `sukl-client.ts` uses `fs.readFileSync` — it is server-only. Never import it in client components.

Medicine lookup by code is O(1) via `medicinesByCode` Map (not linear scan). All SUKL codes are normalized (leading zeros stripped) via `normalizeCode()` consistently across medicines and reimbursements.

### Demo: Guided Tour system

The demo section uses a state machine orchestrator pattern:

- `guided-tour.tsx` — `useReducer` state machine: `intro -> step-1 -> step-2 -> step-3 -> complete -> free`
- Steps chain data: step 1 search returns SUKL code -> step 2 uses it for detail -> step 2 returns ATC -> step 3 uses it
- `chat-widget.tsx` supports two modes via `mode` prop: `"guided"` (single suggested query) and `"free"` (enriched example chips)
- `localStorage` keys `sukl-tour-complete` / `sukl-tour-skipped` skip tour for returning visitors
- `GuidedTour` is lazy-loaded via `next/dynamic` in `demo-section.tsx` to defer framer-motion bundle

### Component layers

- `src/components/sections/` — 13 landing page sections (stateless, visual) incl. `pricing.tsx`
- `src/components/forms/` — Modal forms: `register-modal.tsx` (Pro tier), `contact-modal.tsx` (Enterprise). Both include GDPR consent, name field, and analytics tracking.
- `src/components/demo/` — 10 demo chat components (guided tour + chat widget + message rendering)
- `src/components/ui/` — 12 reusable animated components (shimmer-button, particles, typing-animation, etc.)
- `src/components/icons/` — SVG icon components (single barrel file, tree-shakeable)
- `src/components/theme-provider.tsx` + `theme-toggle.tsx` — Dark/light mode via next-themes

## Coding Conventions

- **No Zod** — Plain TypeScript interfaces in `src/lib/types.ts`. Input validation uses `ValidationError` class in `mcp-handler.ts` (not string-prefix matching).
- **No xMCP framework** — MCP tools are plain functions in `mcp-handler.ts` calling `sukl-client.ts`
- **Czech UI text** — All user-facing strings must be in Czech
- **Tailwind CSS 4** — Theming via CSS variables defined in `globals.css`:
  - Brand: `--sukl-navy`, `--sukl-blue`, `--sukl-light-blue`, `--sukl-accent`
  - Semantic: `--background`, `--foreground`, `--card`, `--border`, `--muted` (light/dark variants)
- **framer-motion** — Used for animations; wrap heavy animated components with `next/dynamic`
- **`@/*` path alias** — Maps to `./src/*` (configured in `tsconfig.json`)
- **Dark/light mode** — `next-themes` with `.light`/`.dark` class on root element

## Data & SUKL APIs

- **Bundled data** (`data/bundled-data.json`, 10.4 MB) — 68k medicines, 2662 pharmacies, 8480 reimbursements, 6907 ATC codes. Must be committed (needed at build time on Vercel).
- **Build scripts** (`scripts/build-pharmacies.ts`, `scripts/build-reimbursements.ts`) — download and process data from SUKL. Handle WIN-1250 encoding.
- **CI automation** (`.github/workflows/update-data.yml`) — monthly cron on 28th day updates bundled data.
- **Document API** — PIL/SPC tools return download URLs from `https://prehledy.sukl.cz/dlp/v1/dokumenty-metadata/{kodSukl}`. PDF parsing via docling-mcp companion.
- **API docs** — `docs/api-reference.md` (tool specs) and `docs/architecture.md` (Mermaid diagrams).

## Deployment

- **Platform:** Vercel, region `fra1` (Frankfurt)
- **Config:** `vercel.json` — rewrites `/mcp` to `/api/mcp`, CORS headers for MCP endpoint
- **Security headers:** CSP, X-Frame-Options, X-Content-Type-Options configured in `next.config.ts`

## Environment Variables

Required for lead capture / Notion CRM (see `.env.example`):

- `NOTION_API_KEY` — Notion integration token
- `NOTION_DB_LEADS` — Database ID for Pro registrations
- `NOTION_DB_ENTERPRISE` — Database ID for Enterprise contacts
- `NOTION_DB_NEWSLETTER` — Database ID for newsletter subscribers

Optional for email notifications (via Resend):

- `RESEND_API_KEY` — Resend API key
- `RESEND_FROM_EMAIL` — Verified sender address (default: `noreply@sukl-mcp.vercel.app`)
- `RESEND_OWNER_EMAIL` — Recipient for enterprise inquiry notifications

Landing page and MCP endpoint work without these (forms will return 500 without Notion keys; emails silently skip without Resend keys).

## Analytics

- **Vercel Analytics** + **Umami** — both initialized in `src/app/layout.tsx`
- `src/lib/analytics.ts` — client-side `trackEvent()` utility that fires to both providers
- Events: `form_open`, `form_submit`, `form_success`, `form_error`, `cta_click`, `pricing_cta`
- CTA section tracks clicks on Smithery install, Pro trial, and GitHub buttons

## Known Constraints

- PIL/SPC returns download URL from SUKL API (prehledy.sukl.cz) — PDF parsing via docling-mcp companion
- In-memory rate limiting resets on serverless cold start
- Cold start may be slow due to 10.4 MB JSON lazy-loading

## Active Technologies
- TypeScript 5+ / Next.js 16.1.6 / React 19.2.3 + `resend` (email), `@notionhq/client` (CRM), `framer-motion` (animace), `lucide-react` (ikony) (001-forms-resend-completion)
- Notion databases (3x: Leads, Enterprise, Newsletter) — external SaaS (001-forms-resend-completion)

## Recent Changes
- 001-forms-resend-completion: Added TypeScript 5+ / Next.js 16.1.6 / React 19.2.3 + `resend` (email), `@notionhq/client` (CRM), `framer-motion` (animace), `lucide-react` (ikony)
