# SUKL MCP Server — API Reference

**Endpoint:** `https://sukl-mcp.vercel.app/mcp`
**Protokol:** JSON-RPC 2.0 over HTTP
**MCP verze:** 2025-03-26
**Rate limit:** 100 req/min per IP

---

## Pripojeni

### MCP klient (Claude, Cursor, atd.)

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

### HTTP metody

| Metoda | Popis |
|--------|-------|
| `POST /mcp` | JSON-RPC 2.0 requesty (initialize, tools/list, tools/call) |
| `GET /mcp` | Server info (nazev, verze, popis) |
| `OPTIONS /mcp` | CORS preflight |

### CORS

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Accept, Mcp-Session-Id
```

---

## JSON-RPC metody

### initialize

Inicializace MCP session.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-03-26",
    "capabilities": {},
    "clientInfo": { "name": "test", "version": "1.0" }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-03-26",
    "capabilities": { "tools": { "listChanged": false } },
    "serverInfo": {
      "name": "sukl-mcp",
      "version": "5.0.0",
      "description": "MCP server pro ceskou databazi lecivych pripravku SUKL (~68k leku)"
    }
  }
}
```

### ping

```json
{ "jsonrpc": "2.0", "id": 2, "method": "ping", "params": {} }
```

Vraci prazdny result `{}`.

### tools/list

Vraci seznam vsech 9 nastroju s popisy a vstupnimi schematy.

### tools/call

Volani konkretniho nastroje.

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "search-medicine",
    "arguments": { "query": "ibuprofen", "limit": 5 }
  }
}
```

### Batch requesty

Pole JSON-RPC objektu se zpracovava paralelne:

```json
[
  { "jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": { "name": "search-medicine", "arguments": { "query": "paralen" } } },
  { "jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": { "name": "search-medicine", "arguments": { "query": "ibuprofen" } } }
]
```

---

## MCP nastroje (9)

### 1. search-medicine

Fuzzy vyhledavani leciv podle nazvu, ucinne latky nebo SUKL kodu.

| Parametr | Typ | Povinny | Popis |
|----------|-----|---------|-------|
| `query` | string | ano | Hledany vyraz (min 2, max 200 znaku) |
| `limit` | number | ne | Max pocet vysledku (1–100, default 20) |

**Priklad:**
```json
{ "name": "search-medicine", "arguments": { "query": "paralen", "limit": 5 } }
```

**Odpoved:**
```json
{
  "medicines": [
    {
      "sukl_code": "0024287",
      "name": "PARALEN 500",
      "strength": "500MG",
      "form": "Tableta",
      "package": "24",
      "atc_code": "N02BE01",
      "substance": "PARACETAMOLUM",
      "holder": "Zentiva",
      "registration_status": "R"
    }
  ],
  "total_count": 15,
  "search_time_ms": 12
}
```

### 2. get-medicine-details

Detailni informace o lecivem pripravku.

| Parametr | Typ | Povinny | Popis |
|----------|-----|---------|-------|
| `sukl_code` | string | ano | SUKL kod (napr. "0024287") |

**Odpoved obsahuje:** Vsechna pole z `MedicineDetail` — registracni cislo, platnost, vydej, forma, baleni, drzitel, ATC, ucinne latky.

### 3. check-availability

Kontrola dostupnosti leciva na trhu.

| Parametr | Typ | Povinny | Popis |
|----------|-----|---------|-------|
| `sukl_code` | string | ano | SUKL kod |

**Odpoved:**
```json
{
  "sukl_code": "0024287",
  "name": "PARALEN 500",
  "status": "available",
  "last_checked": "2026-02-20T00:00:00.000Z",
  "distribution_status": null,
  "expected_availability": null,
  "notes": "Data based on registration status."
}
```

**Statusy:** `available` | `limited` | `unavailable` | `unknown`

### 4. find-pharmacies

Vyhledani lekaren podle mesta, PSC nebo 24h provozu.

| Parametr | Typ | Povinny | Popis |
|----------|-----|---------|-------|
| `city` | string | ne | Nazev mesta (case-insensitive) |
| `postal_code` | string | ne | Postovni smerovaci cislo |
| `is_24h` | boolean | ne | Pouze 24h lekarny |

**Priklad:**
```json
{ "name": "find-pharmacies", "arguments": { "city": "Praha", "is_24h": true } }
```

### 5. get-atc-info

ATC klasifikace leciv.

| Parametr | Typ | Povinny | Popis |
|----------|-----|---------|-------|
| `atc_code` | string | ano | ATC kod (napr. "N02BE01") |
| `include_medicines` | boolean | ne | Zahrnout seznam leciv (default false) |
| `medicines_limit` | number | ne | Max pocet leciv (1–100, default 20) |

**Odpoved:**
```json
{
  "code": "N02BE01",
  "name_cs": "Paracetamol",
  "name_en": null,
  "level": 5,
  "parent_code": "N02BE",
  "description": null
}
```

### 6. get-reimbursement

Informace o uhradach, cenach a doplatcich.

| Parametr | Typ | Povinny | Popis |
|----------|-----|---------|-------|
| `sukl_code` | string | ano | SUKL kod |

**Odpoved:**
```json
{
  "sukl_code": "0094156",
  "reimbursement_group": "P",
  "max_price": 45.5,
  "reimbursement_amount": 32.0,
  "patient_surcharge": 13.5,
  "reimbursement_conditions": null,
  "valid_from": null,
  "valid_until": null
}
```

### 7. get-pil-content

Pribalovy letak (PIL) — metadata a URL ke stazeni z SUKL API.

| Parametr | Typ | Povinny | Popis |
|----------|-----|---------|-------|
| `sukl_code` | string | ano | SUKL kod |

**Odpoved:** `DocumentContent` objekt s `document_url` ke stazeni PDF.

> PDF neni parsovany — pro extrakci textu pouzijte [docling-mcp](https://github.com/docling-project/docling).

### 8. get-spc-content

Souhrn udaju o pripravku (SPC) — metadata a URL ke stazeni.

Stejna signatura jako `get-pil-content`.

### 9. batch-check-availability

Hromadna kontrola dostupnosti (max 50 leciv najednou).

| Parametr | Typ | Povinny | Popis |
|----------|-----|---------|-------|
| `sukl_codes` | string[] | ano | Pole SUKL kodu (max 50 polozek) |

**Odpoved:**
```json
{
  "results": [ /* pole AvailabilityInfo */ ],
  "total_checked": 3,
  "available_count": 2,
  "unavailable_count": 1,
  "checked_at": "2026-02-20T14:00:00.000Z"
}
```

---

## Chybove odpovedi

### JSON-RPC chyby

| Kod | Popis |
|-----|-------|
| `-32700` | Parse error — nevalidni JSON |
| `-32601` | Method not found |
| `-32000` | Rate limit exceeded (HTTP 429) |

### Tool chyby

Chyby nastroju jsou vraceny v `content[0].text` jako textovy popis:

- **Validacni:** `"Parametr 'query' musi byt neprazdny retezec."` — pri chybejicim/prazdnem parametru
- **Nenalezeno:** `"Lek s SUKL kodem 'XXXX' nebyl nalezen."` — lek neexistuje v databazi
- **Obecna:** `"Chyba pri zpracovani pozadavku. Zkuste to znovu."` — runtime chyba (detaily v serverovem logu)

---

## Datove typy

### MedicineBasic

```typescript
interface MedicineBasic {
  sukl_code: string;
  name: string;
  strength: string | null;
  form: string | null;
  package: string | null;
  atc_code: string | null;
  substance: string | null;
  holder: string | null;
  registration_status: string | null;
}
```

### MedicineDetail (extends MedicineBasic)

Pridava: `registration_number`, `registration_valid_until`, `dispensing`, `legal_status`, `route_of_administration`, `indication_group`, `mrp_number`, `parallel_import`.

### ReimbursementInfo

```typescript
interface ReimbursementInfo {
  sukl_code: string;
  reimbursement_group: string | null;
  max_price: number | null;        // CZK
  reimbursement_amount: number | null; // CZK
  patient_surcharge: number | null;  // CZK (max_price - reimbursement_amount)
  reimbursement_conditions: string | null;
  valid_from: string | null;
  valid_until: string | null;
}
```

### Pharmacy

```typescript
interface Pharmacy {
  id: string;
  name: string;
  address: string | null;
  city: string | null;
  postal_code: string | null;
  phone: string | null;
  email: string | null;
  opening_hours: string | null;
  latitude: number | null;
  longitude: number | null;
  distance_km: number | null;
  is_24h: boolean;
  has_erecept: boolean;
}
```

### ATCInfo

```typescript
interface ATCInfo {
  code: string;
  name_cs: string;
  name_en: string | null;
  level: number;          // 1-5 (ATC hierarchy)
  parent_code: string | null;
  description: string | null;
}
```

---

## Demo API

**Endpoint:** `POST /api/demo`
**Rate limit:** 10 req/min per IP
**Ucel:** Backend pro interaktivni demo chat (bez LLM)

**Request:**
```json
{ "query": "paralen" }
```

**Intent parser** automaticky rozpozna typ dotazu:
- SUKL kod (4–7 cislic) → detail leciva
- ATC kod (napr. "N02BE01") → ATC info
- Klicove slovo "lekarna" + mesto → vyhledani lekaren
- Ostatni → fuzzy hledani leciv

**Response:** Obsahuje `time_ms` pro mereni vykonnosti.
