# SÚKL MCP jako veřejný plugin ChatGPT

Lokální kandidát aplikace v6.0.0, pluginového balíčku v1.0.0. Výchozí remote main: `ee988dfb4fede38a5642a86287348d4e039cc015`. Změny nejsou na GitHubu ani na veřejném serveru. Cílem je používání katalogu během běžných konverzací v ChatGPT; integrace do EHR není součástí tohoto vydání.

## Veřejná funkce

Plugin je zdarma, bez účtu a bez OAuth. Pět nástrojů: `search_medicines`, `get_medicine`, `get_atc_group`, `get_medicine_document`, `display_medicines`. Nástroje jsou pouze pro čtení, mají explicitní anotace a bezpečnostní schéma `noauth`. Vrací strukturovaná i textová data; grafiku připojuje pouze poslední nástroj. Karty mají inline JS/CSS, podporují téma hostitele a žádné externí zdroje, analytiku ani iframe. PIL/SPC se otevírá na výslovné kliknutí uživatele přes hostitelský `openLink`. UI nečte historii chatu.

Veřejný endpoint: `https://sukl-mcp.vercel.app/chatgpt/mcp` **po nasazení**, nyní je připravován lokálně. Obsahuje pouze informační katalog a odkazy na dokumenty. Neobsahuje nákupy, osobní doporučení léčby, zásoby ani ceny/úhrady. Opravené SCAU údaje zůstávají dostupné původním klientům přes `/mcp`, s datem platnosti a vysvětlením výpočtu.

`display_medicines` připojuje `ui://sukl-catalogue/medicines-v1.html`. Změna kompatibility widgetu vyžaduje novou URI. Dev náhled `/api/chatgpt/preview` a `/api/chatgpt/preview-data` vrací v produkci 404. Tlačítka v dev náhledu jsou záměrně vypnutá: náhled ověřuje rozvržení, ne skutečné připojení do ChatGPT.

## Data

Aktuální import: 69 847 přípravků, 6 999 ATC záznamů, 2 689 lékáren, 8 626 úhrad. DLP platí od 1. 10. do 31. 10. 2026. Ceny/úhrady SCAU od 1. 10. 2026. Zdrojová URL, SHA-256 a platnost jsou v `data/bundled-data.json` pod `_.sources`.

`npm run data:update` objeví archiv na oficiální stránce DLP a aktuální účinný SCAU v21 v oficiálním katalogu. Importuje i složení, názvy držitelů, registrační čísla a dostupné další údaje. Lékárenský CSV zdroj nemá potvrzenou dobu platnosti; nelze z něj potvrdit otevírací dobu. Příznak pohotovosti není 24/7 provoz.

Import kontroluje hlavičky a formát CSV, počty, unikátní kódy, ATC reference, 122 polí SCAU v21 a částky. Nejprve zpracuje všechny soubory, pak zapíše celý balíček atomicky. Při chybě ponechá předchozí data. Opakovaný import stejných zdrojů nezmění soubor. Změna schématu SCAU vyžaduje ruční kontrolu parseru, ne tiché hádání sloupců.

ATC ve zdroji obsahuje jednu mezeru: `V06XX` nemá záznam `V06X`. `parent_code` je proto null a mezera je zapsána v metadatech. Nadřazený záznam se nevymýšlí. Je to nedostatek zdrojových dat, nikoli potvrzení jiné klasifikace.

Provenance odděluje čas sestavení od platnosti zdroje. Po uplynutí platnosti označí snímek jako expired a připojí upozornění. Workflow vytvoří nebo aktualizuje jednu PR `automated/sukl-data`; data se bez schválení PR sama nedostanou do nasazené služby. Provozovatel musí aktualizace včas sloučit a nasadit.

## Opravy nálezů auditu

| Nález | Stav lokálního kódu |
|---|---|
| 1. Chybné úhrady | MFC sloupec 86, UHR1 sloupec 19; OME1 je preskripční omezení. Doplatek je maximum MFC − UHR1, nikoli garantovaná cena v lékárně. Parser má nezávislý regresní příklad. |
| 2. Registrace vydávaná za dostupnost | Dostupnost známých přípravků je unknown, bez falešného času ověření. Veřejný plugin tuto funkci nepropaguje. |
| 3. Zastaralý katalog | Nový atomický import obnovuje léčiva, ATC, složení, lékárny i úhrady. Aktuální říjnový import je uložen. Živý workflow a jeho oprávnění zůstávají k ověření. |
| 4. ATC hierarchie | Úrovně a rodiče odpovídají délkám 1/3/4/5/7, chybějící rodič ze zdroje je null. |
| 5. Ztracené kódy v dávce | Původní batch vrací i not_found a samostatné počty unknown/not_found. |
| 6. MCP transport | Oba HTTP endpointy používají oficiální SDK, stateless JSON odpovědi; GET/DELETE 405, notifications 202, validační/provozní chyby rozlišeny, Origin allowlist. |
| 7. Neomezená cena požadavku | Max. 16 KiB těla, zákaz JSON-RPC dávek, limity výsledků a kódů, paginace lékáren, přísné parametry. Veřejný režim vyžaduje sdílený Redis limiter; lokální fallback je jen pro přípravu. |
| 8. Závislosti | Aktualizovaný Next.js a lockfile. Poslední lokální npm audit: 0 známých nálezů. Nejde o garanci všech typů bezpečnosti. |
| 9. Chybějící soukromí | Připraveny /privacy, /terms, /chatgpt/support a produktová stránka. Právní stránky jsou návrhy a vrací 503, dokud provozovatel nepotvrdí skutečné nastavení a uchování. |
| 10. Emaily | HTML escape všech uživatelských hodnot, Resend error objekty vedou k chybě, absence emailových credentials znamená vědomé přeskočení odeslání. Samostatné formuláře mají serverový čas souhlasu a lepší validaci. |
| 11. Počet hledání | Celkový počet není omezen velikostí stránky; přesný SÚKL kód má přednost. |
| 12. Neúplné detaily | Doplněné složení z dostupných aktivních složek a další katalogové údaje; neznámé jsou null. Katalog není individuální léčebné doporučení. |
| 13. Dokumenty | Timeout 8 s, kontrola tvaru a ID, normalizované kódy; veřejný nástroj rozlišuje nenalezený přípravek, dokument a chybu zdroje. Vrací odkaz, ne přečtený PDF obsah. |
| 14. CI a testy | Nový test/build/package/audit gate a idempotentní data PR. Lokální testy používají skutečný MCP SDK klient a kontrolují nejrizikovější negativní případy. Aktivní ochrana main a funkčnost GitHub Actions nejsou tímto doloženy. |
| 15. UI a analytika | Omezené seznamy, lepší parser ATC/českých měst, opravená Enterprise CTA, odstraněné tvrzení o léčivech v reálném čase. Umami odstraněno, Vercel analytics vypnuta ve výchozím nastavení. |

Newsletter používá aktuální Notion data-source API a při výpadku kontroly nepokračuje zápisem. Pro volitelné zapnutí vyžaduje sdílený Redis lease (atomické SET NX, uvolnění pouze vlastníkem), takže kontrola/vytvoření záznamu neběží současně ve více instancích. Je nutné ověřit konkrétní Notion databázi, poskytovatele Redis, podmínky a doručování; lokální test používá syntetické odpovědi, ne skutečné kontakty. Produkční webové formuláře jsou ve výchozím nastavení deaktivované.

## Sestavení a kontrola

```bash
npm ci
npm run data:update
npm run build:widget
npm test
npm run build
npm run plugin:package
npm run plugin:check
npm audit --omit=dev
```

Balíček je v `plugin-dist/sukl-medicines-1.0.0.zip`; uvnitř jsou root `plugin.json`, `mcp.json`, onboarding skill, nezávislá ikona a licence. Není v něm serverový kód ani credentials. Server se nasazuje zvlášť. `.app.json` a hooks nejsou součástí ZIP, protože je současný veřejný submission nepřijímá.

Před změnou domény sestavte ZIP s `PLUGIN_BASE_URL=https://vas-overeny-host`. Widget origin nastavte v `MCP_WIDGET_DOMAIN`, veřejný serverový origin v `MCP_PUBLIC_ORIGIN`. Origin zásadně neměňte po publikaci bez kontroly procesu OpenAI: změna původu MCP může vyžadovat nový plugin.

`PLUGIN_DEMO_URL` přijme skutečný veřejný odkaz na video, ne zástupný odkaz. ZIP obsahuje přesně pět pozitivních a tři negativní review scénáře. Scénáře popisují očekávání; nejsou důkazem úspěšného testu přímo v ChatGPT.

## Co vyžaduje skutečný účet nebo hosting

1. Zkontrolovat diff kandidáta v6.0.0 a vydání nasadit na veřejný HTTPS host. Zachovávat bundle a widget ve Vercel file tracing. Ověřit dostupnost včetně cold startu.
2. Nastavit sdílený Redis limit, soukromý HMAC salt, `PUBLIC_LAUNCH_MODE=true`. Před spuštěním ověřit dostupnost Redis, TTL a chování při výpadku. Aplikace pak vrací 503 místo obcházení ochrany. Zabezpečit server i proti distribuovanému zneužití na vrstvě hostingu, podle očekávaného zatížení.
3. Doplnit skutečného poskytovatele Redis a potvrzené doby uchování hostingu/formulářů. Zkontrolovat podmínky použití zdrojových dat a zpracovatelské vztahy. Až pak potvrdit `PUBLICATION_POLICY_CONFIRMED=true`. Nechat formuláře a analytiku vypnuté, pokud nejsou potřebné.
4. Pustit lokálně klientský readback `npm run plugin:check -- --live`. Vyžaduje veřejné stránky, skutečné video, připravenost služby, pět nástrojů, aktuální katalog a UI resource. Úspěšný readback ještě není schválení OpenAI.
5. V ChatGPT developer mode připojit veřejný endpoint a bez autentizace zkusit pět pozitivních a tři negativní scénáře. Ověřit widget, kliknutí na PIL/SPC, textový fallback, chybu zdroje a použití bez zadání osobních údajů. Po změně toolů aktualizovat import. Zaznamenat skutečný průchod pro reviewer video.
6. V OpenAI organizaci zvolit ověřenou individuální identitu Petra Sovadiny, nebo odpovídající ověřenou firmu, má-li být skutečným vydavatelem. Pro MCP review potřebujete podporovaný projekt s global data residency a právo Apps Management Write. Tato oprávnění nejsou lokálními testy ověřena.
7. V https://platform.openai.com/plugins nahrát ZIP, připojit MCP, dokončit doménovou verifikaci podle portálu, Scan Tools, odstranit findings a odeslat k review. Schválení je samostatné od Publish. Po schválení zveřejnit a ověřit přesné jméno nebo URL katalogu. Publikace nezaručuje umístění na hlavní stránce katalogu.
8. Nastavit požadované CI checks na main, opravit účtové/runner blokace GitHub Actions a ověřit první skutečnou data PR. Lokální build nemůže potvrdit, že starý problém spouštění Actions zmizel.

## Změny pro původní klienty v6

JSON-RPC HTTP dávky nejsou podporovány. `find-pharmacies` vrací objekt `{pharmacies,total_count,offset,limit,provenance}`, ne holé pole. Neověřený filtr is_24h vrací chybu. Číselné parametry musí být skutečná celá čísla v deklarovaném rozsahu. Tool výsledky mají structuredContent a provenance; validační a provozní chyby nesou isError. Dostupnost je unknown a batch zachovává nenalezené kódy. Úhrady mají opravenou semantiku a datum platnosti. Proto jde o novou hlavní verzi, nikoli o bezezměnový upgrade původních kontraktů.

## Primární dokumentace

- https://developers.openai.com/plugins/build/plugins
- https://developers.openai.com/plugins/build/chatgpt-ui
- https://developers.openai.com/plugins/deploy/submission
- https://developers.openai.com/plugins/deploy/app-review
- https://developers.openai.com/plugins/plugin-guidelines
- https://opendata.sukl.gov.cz/?q=katalog/databaze-lecivych-pripravku-dlp
- https://sukl.gov.cz/ceny-a-uhrady-leciv/seznam-cen-a-uhrad-lp/seznam-cen-a-uhrad-lp-k-1-10-2026/
- https://sukl.gov.cz/wp-content/uploads/2025/12/Datove-rozhrani-SUKL-Seznam-hrazenych-LP_260101_verze-21.pdf
- https://vercel.com/docs/headers/request-headers

Ověřeno podle dokumentace a zdrojů k 3. 10. 2026. Portál, approval, doménová verifikace, skutečná výkonnost a end-to-end ChatGPT zůstávají před publikací k ověření.
