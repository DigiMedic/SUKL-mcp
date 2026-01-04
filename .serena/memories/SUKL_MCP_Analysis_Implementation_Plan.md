# Analýza a implementační plán pro SUKL MCP Server

## 📊 Aktuální stav projektu

### 1. Datová vrstva
- **`SUKLDataLoader`**: Zajišťuje asynchronní stahování a extrakci ZIP souborů z Open Dat SÚKL.
  - Bezpečnost: Ochrana proti ZIP bombám (max. 5 GB extrahovaných dat).
  - Úložiště: Ukládá data do mezipaměti v `/tmp/sukl_dlp_cache`.
- **`SUKLClient`**: Thread-safe singleton spravující pandas DataFramy.
  - Vzor: Double-checked locking pro inicializaci.
  - Vyhledávání: Víceúrovňová pipeline (Látka -> Přesný název -> Podřetězec -> Fuzzy).

### 2. API vrstva
- Postaveno na **FastMCP** (FastAPI + Pydantic).
- Nástroje registrované pomocí `@mcp.tool`.
- Správa životního cyklu pomocí `@asynccontextmanager` pro obsluhu spuštění a ukončení klienta.

### 3. Modely
- Modely **Pydantic v2** pro všechny datové struktury.
- Používejte `Field(..., description="...")` pro poskytnutí kontextu LLM modelům využívajícím tyto nástroje.
- Enumy pro pevné sady hodnot jako `RegistrationStatus` nebo `AvailabilityStatus`.

## 🐛 Známé problémy a technické dluhy
- **Zastaralá data**: CSV se stahují při startu, nejsou real-time.
- **Duplicita kódu**: Dva klienti pro stejná data.
- **Nekonzistence**: Některé tools používají API, jiné CSV.
- **Zbytečná paměť**: ~68k léčiv v pandas DataFrame v RAM.

## 🎯 Cílová architektura
- **Unified API Client**: Vytvoření nového klienta pro SÚKL REST API.
- **Real-time data**: Přechod na real-time API pro aktuální informace.
- **Nižší paměť**: Eliminace potřeby velkých pandas DataFrame.

## 📋 Implementační plán

### Fáze 1: Nový API klient (2-3 dny)
- Vytvoření `SUKLAPIClient` s retry logikou a caching.
- Implementace metod pro vyhledávání léčiv, lékáren a distributorů.

### Fáze 2: Migrace tools (1-2 dny)
- Aktualizace existujících tools pro použití nového API klienta.

### Fáze 3: Odstranění CSV kódu (1 den)
- Odstranění `client_csv.py` a souvisejících souborů.

### Fáze 4: Aktualizace testů (1 den)
- Přidání testů pro nový API klient a aktualizace stávajících testů.

## ⚠️ Rizika a mitigace
- **API nedostupnost**: Implementace retry logiky.
- **Rate limiting**: Throttling pro API volání.
- **API změny**: Verzování a testy pro zajištění stability.

## ✅ Checklist migrace
- [ ] Vytvořit nový `SUKLAPIClient`.
- [ ] Implementovat response caching.
- [ ] Migrovat tools.
- [ ] Přidat smoke testy.
- [ ] Aktualizovat dokumentaci.
- [ ] Odstranit `client_csv.py`.
- [ ] Release v4.0.0.

---