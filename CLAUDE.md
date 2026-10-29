# Repository guidance

Current application v6.0.2; public plugin package v1.0.1. Read README.md and docs/openai-publication.md first. Historical v5 API/architecture documents are not authoritative for current contracts.

## Contracts and implementation

- `/chatgpt/mcp`: five read-only public catalogue tools, official MCP SDK, explicit output schemas in src/lib/catalogue-schema.ts, stateless JSON HTTP, no JSON-RPC batches. Only display_medicines renders cards. Document links need model and app visibility for widget clicks.
- `/mcp` rewrites to `/api/mcp`: nine legacy tools using the same transport. Known stock is unknown; unverified is_24h filtering is rejected; pharmacy results are paginated objects, not arrays. Codes retain seven-digit padding.
- src/lib/sukl-client.ts uses the committed server-only bundled data; never import it in client components. Unknown values remain null. Do not infer stock from registration, invent missing ATC parents or turn PIL links into claims that PDF contents were read.
- widgets/medicines.ts is bundled inline. MCP SDK 1.32.0 and ext-apps 1.7.5 are pinned together. A dependency upgrade must pass tests/api/widget-bridge.test.ts and real browser interaction, not only a static preview. Change the UI URI after incompatible widget changes.
- Tool logs contain operation, outcome and duration only; never log arguments, results, IP addresses or secrets.
- Public launch requires shared Redis limits and confirmed real policies. Never invent retention, provider details, review video, identity or a domain challenge token. Default analytics and legacy forms remain disabled.

## Commands and checks

npm ci; npm test; npm run build; npm run plugin:package; npm run plugin:check; npm audit --omit=dev.
node scripts/smoke-mcp.mjs https://sukl-mcp.vercel.app checks both live endpoints. npm run plugin:check -- --live aggregates technical publication blockers; it does not establish actual ChatGPT host behavior or OpenAI approval.
npm run data:update validates and atomically imports official sources; the monthly workflow proposes a data PR. Verify GitHub Actions actually starts: account billing locked it on 2026-10-03.

## Conventions

Czech user-facing text, TypeScript strict mode, explicit input validation, null unknowns, source validity and attribution on outputs, independent branding. MIT covers software only; redistributed SÚKL open data must link its conditions. Preserve Vercel file tracing for data and widget HTML. No secrets in plugin ZIP, code, examples or logs.
