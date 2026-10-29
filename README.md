# SÚKL MCP — katalog léčiv pro ChatGPT

Nezávislý projekt Petra Sovadiny pro vyhledávání českých léčivých přípravků během konverzací. Aplikace v6.0.2, balíček pluginu v1.0.1. Veřejná služba běží na Vercelu; publikace v katalogu OpenAI ještě není dokončena. Podrobný stav, omezení a publikační postup jsou v [docs/openai-publication.md](docs/openai-publication.md).

- Produktová stránka: https://sukl-mcp.vercel.app/chatgpt
- Veřejný ChatGPT MCP: https://sukl-mcp.vercel.app/chatgpt/mcp
- Původní MCP klienti: https://sukl-mcp.vercel.app/mcp
- Připravenost služby: https://sukl-mcp.vercel.app/chatgpt/status

## Funkce

| Nástroj ChatGPT | Funkce |
|---|---|
| `search_medicines` | Název, uvedená účinná látka nebo kód SÚKL |
| `get_medicine` | Přesný katalogový záznam |
| `get_atc_group` | ATC skupina, rodič a omezený seznam přípravků |
| `get_medicine_document` | Oficiální odkaz na PIL/SPC, bez předstírání přečtení PDF |
| `display_medicines` | Karty přípravků přes MCP Apps v konverzaci |

Bez uživatelského účtu a OAuth, pouze čtení. Výsledky obsahují platnost a zdroj dat. Plugin neposkytuje individuální léčebná doporučení, aktuální skladovou dostupnost ani nákup léčiv. Ceny/úhrady a lékárny jsou pouze v původním rozhraní s devíti nástroji; známá dostupnost je `unknown`, nikoli odhad zásob. Změny jeho kontraktu proti v5 jsou v publikačním návodu. Starší `docs/api-reference.md` a `docs/architecture.md` nejsou autoritou pro nový kontrakt.

Katalog obsahuje 69 847 přípravků, 6 999 ATC záznamů, 2 689 lékáren a 8 626 úhrad. DLP platí 1.–31. 10. 2026, SCAU od 1. 10. 2026. Po konci platnosti služba snímek označí jako zastaralý. Zdrojové URL a SHA-256 jsou v `data/bundled-data.json`; počty webu vznikají z `data/catalogue-summary.json`.

## Vývoj a ověření

```bash
npm ci
npm run dev
npm test
npm run build
npm run plugin:package
npm run plugin:check
node scripts/smoke-mcp.mjs https://sukl-mcp.vercel.app
npm run plugin:check -- --live
npm audit --omit=dev
```

Build automaticky vytvoří inline widget. ZIP v `plugin-dist/` obsahuje manifest Agent Plugins 1.0, jednu MCP konfiguraci, onboarding, vlastní ikonu a licenci; neobsahuje server ani secrets. Live checker zapíše úplný výsledek do `plugin-dist/validation-report.json` i při blokované publikaci. Kontrola přes MCP SDK a lokální MCP Apps bridge nenahrazuje test přímo v ChatGPT ani review OpenAI.

## Data a provoz

`npm run data:update` načte oficiální DLP/SCAU/lékárny, zkontroluje formát a reference a zapíše bundle atomicky. Opakování stejného importu nic nezmění. Měsíční GitHub workflow připravuje datovou PR, kterou je nutné sloučit a nasadit. K 3. 10. 2026 jsou GitHub Actions blokovány účtovým problémem s billingem; automatické aktualizace tím nejsou ověřeny jako funkční.

Next.js 16.3.8, React 19.2.3, MCP SDK 1.32.0, MCP Apps 1.7.5. Tyto verze SDK jsou společně připnuté; aktualizace musí projít testem volání widget → hostitel → nástroj. Podrobnosti jsou v publikačním návodu. Node 24 na Vercelu, region Frankfurt. Datový bundle i widget jsou zahrnuty ve file tracing. Datovou vrstvu neimportujte do klientských komponent.

Nastavení je v `.env.example`. Veřejné spuštění vyžaduje sdílený Redis limiter, HMAC salt, potvrzené skutečné podmínky zpracování a uchování, a `PUBLIC_LAUNCH_MODE=true`. Při výpadku limiteru se služba v tomto režimu uzavře s 503. Přípravný režim používá omezení v paměti každé instance. Analytika a starší formuláře jsou ve výchozím stavu vypnuté. Pro jejich volitelné zapnutí je nutné ověřit také Redis lease, Notion databáze, souhlasy a doručování.

## Licence a zdroje

Software: [MIT](LICENSE). Data: [SÚKL](https://opendata.sukl.gov.cz/) a jeho [podmínky užití otevřených dat](https://opendata.sukl.gov.cz/?q=podminky-uziti-otevrenych-dat). MIT se nevztahuje na data SÚKL ani dokumenty třetích stran. Projekt není oficiální aplikací SÚKL a nevyjadřuje podporu této instituce.
