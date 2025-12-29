# API Reference

## Overview

The SÚKL MCP Server exposes 7 MCP tools for accessing Czech pharmaceutical data. All tools are async and return structured Pydantic models serialized to JSON.

**Base URL** (HTTP transport): `http://localhost:8000`
**Transport**: stdio (FastMCP Cloud) or HTTP/SSE (Smithery)
**Protocol**: Model Context Protocol (MCP)

## MCP Tools

### 1. search_medicine

Search for medicines in the SÚKL database by name, active substance, or ATC code.

**Location**: `/src/sukl_mcp/server.py` (lines 72-136)

#### Signature

```python
async def search_medicine(
    query: str,
    only_available: bool = False,
    only_reimbursed: bool = False,
    limit: int = 20,
) -> SearchResponse
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search text: medicine name, active substance, or ATC code |
| `only_available` | boolean | No | `false` | Filter to only medicines available on the market |
| `only_reimbursed` | boolean | No | `false` | Filter to only reimbursed medicines |
| `limit` | integer | No | `20` | Maximum number of results (1-100) |

#### Return Type

```typescript
interface SearchResponse {
  query: string;                    // Original search query
  total_results: number;            // Number of results found
  results: MedicineSearchResult[];  // Array of medicine results
  search_time_ms: number | null;    // Search duration in milliseconds
}

interface MedicineSearchResult {
  sukl_code: string;              // SÚKL code (7 digits)
  name: string;                   // Medicine name
  supplement: string | null;      // Name supplement
  strength: string | null;        // Strength (e.g., "500mg")
  form: string | null;            // Pharmaceutical form (e.g., "tableta")
  package: string | null;         // Package size
  atc_code: string | null;        // ATC classification code
  registration_status: string | null;  // Registration status
  dispensation_mode: string | null;    // Dispensation mode (Rp, F, Lp, etc.)
  is_available: boolean | null;   // Market availability
  has_reimbursement: boolean | null;  // Reimbursement status
}
```

#### Examples

**Search by medicine name**:
```json
{
  "tool": "search_medicine",
  "params": {
    "query": "ibuprofen",
    "limit": 5
  }
}
```

**Response**:
```json
{
  "query": "ibuprofen",
  "total_results": 5,
  "results": [
    {
      "sukl_code": "0123456",
      "name": "IBUPROFEN",
      "supplement": "Zentiva",
      "strength": "400mg",
      "form": "tableta",
      "package": "30",
      "atc_code": "M01AE01",
      "registration_status": "R",
      "dispensation_mode": "Rp",
      "is_available": true,
      "has_reimbursement": true
    }
  ],
  "search_time_ms": 127.5
}
```

**Search by ATC code** (analgesics):
```json
{
  "tool": "search_medicine",
  "params": {
    "query": "N02",
    "only_available": true,
    "limit": 20
  }
}
```

**Search with filters**:
```json
{
  "tool": "search_medicine",
  "params": {
    "query": "Paralen",
    "only_reimbursed": true,
    "limit": 10
  }
}
```

#### Error Codes

| Error | Cause | HTTP Status |
|-------|-------|-------------|
| `SUKLValidationError` | Empty query or length > 200 chars | 400 |
| `SUKLValidationError` | Invalid limit (not 1-100) | 400 |
| `SUKLDataError` | Data not loaded | 500 |

#### Performance

- **Typical Latency**: 50-150ms for common queries
- **Complexity**: O(n) - full DataFrame scan
- **Cache**: No caching (always fresh results)

---

### 2. get_medicine_details

Get comprehensive information about a specific medicine by SÚKL code.

**Location**: `/src/sukl_mcp/server.py` (lines 138-196)

#### Signature

```python
async def get_medicine_details(sukl_code: str) -> MedicineDetail | None
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sukl_code` | string | Yes | SÚKL code (7 digits, e.g., "0012345" or "12345") |

**Note**: Leading zeros are optional - "12345" is automatically normalized to "0012345".

#### Return Type

```typescript
interface MedicineDetail {
  // Basic identification
  sukl_code: string;              // SÚKL code (7 digits)
  name: string;                   // Medicine name
  supplement: string | null;      // Name supplement

  // Composition and form
  strength: string | null;        // Strength
  form: string | null;            // Pharmaceutical form
  route: string | null;           // Route of administration
  package_size: string | null;    // Package size
  package_type: string | null;    // Package type

  // Registration
  registration_number: string | null;  // Registration number
  registration_status: string | null;  // Status (R, B, C, P, D)
  registration_holder: string | null;  // Marketing authorization holder

  // Classification
  atc_code: string | null;        // ATC WHO code
  atc_name: string | null;        // ATC group name
  dispensation_mode: string | null;  // Dispensation mode

  // Availability
  is_available: boolean | null;   // Market availability
  is_marketed: boolean | null;    // Currently marketed

  // Reimbursement (TODO: Limited data)
  has_reimbursement: boolean | null;
  max_price: number | null;
  reimbursement_amount: number | null;
  patient_copay: number | null;

  // Documents
  pil_available: boolean;         // Patient information leaflet
  spc_available: boolean;         // Summary of product characteristics

  // Special flags
  is_narcotic: boolean;           // Narcotic substance
  is_psychotropic: boolean;       // Psychotropic substance
  is_doping: boolean;             // Doping substance

  last_updated: string | null;    // ISO 8601 timestamp
}
```

#### Examples

**Get medicine details**:
```json
{
  "tool": "get_medicine_details",
  "params": {
    "sukl_code": "254045"
  }
}
```

**Response**:
```json
{
  "sukl_code": "0254045",
  "name": "PARALEN 500",
  "supplement": null,
  "strength": "500mg",
  "form": "tableta",
  "route": "perorální podání",
  "package_size": "30",
  "package_type": "blistr",
  "registration_number": "16/123/45-C",
  "registration_status": "R",
  "registration_holder": "Zentiva k.s.",
  "atc_code": "N02BE01",
  "atc_name": null,
  "dispensation_mode": "Rp",
  "is_available": true,
  "is_marketed": true,
  "has_reimbursement": false,
  "max_price": null,
  "reimbursement_amount": null,
  "patient_copay": null,
  "pil_available": false,
  "spc_available": false,
  "is_narcotic": false,
  "is_psychotropic": false,
  "is_doping": false,
  "last_updated": "2024-12-29T10:30:00Z"
}
```

**Medicine not found**:
```json
{
  "tool": "get_medicine_details",
  "params": {
    "sukl_code": "9999999"
  }
}
```

**Response**:
```json
null
```

#### Error Codes

| Error | Cause | HTTP Status |
|-------|-------|-------------|
| `SUKLValidationError` | Empty SÚKL code | 400 |
| `SUKLValidationError` | Non-numeric code | 400 |
| `SUKLValidationError` | Length > 7 characters | 400 |

#### Performance

- **Typical Latency**: 5-20ms
- **Complexity**: O(n) - DataFrame filter
- **Optimization**: Returns `None` immediately if code not found

---

### 3. get_pil_content

Get the Patient Information Leaflet (PIL) for a medicine.

**Location**: `/src/sukl_mcp/server.py` (lines 198-229)

#### Signature

```python
async def get_pil_content(sukl_code: str) -> PILContent | None
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sukl_code` | string | Yes | SÚKL code (7 digits) |

#### Return Type

```typescript
interface PILContent {
  sukl_code: string;           // SÚKL code
  medicine_name: string;       // Medicine name
  document_url: string | null; // URL to PDF document
  language: string;            // Document language (default: "cs")
  full_text: string | null;    // Text content (currently: URL reference)
}
```

#### Examples

**Get PIL**:
```json
{
  "tool": "get_pil_content",
  "params": {
    "sukl_code": "254045"
  }
}
```

**Response**:
```json
{
  "sukl_code": "0254045",
  "medicine_name": "PARALEN 500",
  "document_url": "https://prehledy.sukl.cz/pil/0254045.pdf",
  "language": "cs",
  "full_text": "Pro kompletní text příbalového letáku navštivte odkaz v document_url. Příbalový leták je dostupný ve formátu PDF na stránkách SÚKL."
}
```

#### Important Notes

- **Disclaimer**: Information is for informational purposes only. Always follow doctor's instructions.
- **Current Implementation**: Returns PDF URL, not full text extraction
- **Language**: Always Czech ("cs")

#### Error Codes

| Error | Cause | HTTP Status |
|-------|-------|-------------|
| Medicine not found | Invalid SÚKL code | Returns `null` |

---

### 4. check_availability

Check current market availability of a medicine.

**Location**: `/src/sukl_mcp/server.py` (lines 231-262)

#### Signature

```python
async def check_availability(sukl_code: str) -> AvailabilityInfo | None
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sukl_code` | string | Yes | SÚKL code (7 digits) |

#### Return Type

```typescript
interface AvailabilityInfo {
  sukl_code: string;                  // SÚKL code
  medicine_name: string;              // Medicine name
  is_available: boolean;              // Currently available
  is_marketed: boolean;               // Currently marketed
  unavailability_reason: string | null;  // Reason if unavailable
  alternatives_available: boolean;    // Has alternatives (always false)
  checked_at: string;                 // ISO 8601 timestamp
}
```

#### Examples

**Check availability**:
```json
{
  "tool": "check_availability",
  "params": {
    "sukl_code": "254045"
  }
}
```

**Response (available)**:
```json
{
  "sukl_code": "0254045",
  "medicine_name": "PARALEN 500",
  "is_available": true,
  "is_marketed": true,
  "unavailability_reason": null,
  "alternatives_available": false,
  "checked_at": "2024-12-29T10:30:00Z"
}
```

**Response (unavailable)**:
```json
{
  "sukl_code": "0123456",
  "medicine_name": "SOME MEDICINE",
  "is_available": false,
  "is_marketed": true,
  "unavailability_reason": "Přípravek není aktuálně dodáván",
  "alternatives_available": false,
  "checked_at": "2024-12-29T10:30:00Z"
}
```

#### Data Source

Availability determined by `DODAVKY` column in DLP data:
- `DODAVKY != "0"`: Available
- `DODAVKY == "0"`: Unavailable

---

### 5. get_reimbursement

Get reimbursement information for a medicine.

**Location**: `/src/sukl_mcp/server.py` (lines 264-301)

#### Signature

```python
async def get_reimbursement(sukl_code: str) -> ReimbursementInfo | None
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sukl_code` | string | Yes | SÚKL code (7 digits) |

#### Return Type

```typescript
interface ReimbursementInfo {
  sukl_code: string;                 // SÚKL code
  medicine_name: string;             // Medicine name
  is_reimbursed: boolean;            // Has reimbursement
  reimbursement_group: string | null;  // Reimbursement group (CAU)
  max_producer_price: number | null;   // Maximum producer price
  max_retail_price: number | null;     // Maximum retail price
  reimbursement_amount: number | null; // Reimbursement amount
  patient_copay: number | null;        // Patient copayment
  has_indication_limit: boolean;     // Indication limitations exist
  indication_limit_text: string | null;  // Limitation text
  specialist_only: boolean;          // Specialist prescription required
}
```

#### Examples

**Get reimbursement info**:
```json
{
  "tool": "get_reimbursement",
  "params": {
    "sukl_code": "254045"
  }
}
```

**Response**:
```json
{
  "sukl_code": "0254045",
  "medicine_name": "PARALEN 500",
  "is_reimbursed": false,
  "reimbursement_group": null,
  "max_producer_price": null,
  "max_retail_price": null,
  "reimbursement_amount": null,
  "patient_copay": null,
  "has_indication_limit": false,
  "indication_limit_text": null,
  "specialist_only": false
}
```

#### Current Limitations

**Limited Data**: Current implementation returns minimal data because:
1. Reimbursement details are in separate CSV files (`dlp_cau_scau.csv`, `dlp_cau_scup.csv`)
2. These files are not currently loaded by SUKLDataLoader

**Future Enhancement**: Load CAU tables to provide:
- Detailed pricing information
- Reimbursement groups
- Indication limitations
- Patient copayment calculations

#### Important Note

Actual copay may vary by:
- Specific health insurance company
- Pharmacy bonus programs
- Patient exemptions

---

### 6. find_pharmacies

Find pharmacies by location and service filters.

**Location**: `/src/sukl_mcp/server.py` (lines 303-367)

#### Signature

```python
async def find_pharmacies(
    city: str | None = None,
    postal_code: str | None = None,
    has_24h_service: bool = False,
    has_internet_sales: bool = False,
    limit: int = 20,
) -> list[PharmacyInfo]
```

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `city` | string | No | `null` | City name (partial match) |
| `postal_code` | string | No | `null` | Postal code (5 digits) |
| `has_24h_service` | boolean | No | `false` | Only 24/7 pharmacies |
| `has_internet_sales` | boolean | No | `false` | Only pharmacies with online sales |
| `limit` | integer | No | `20` | Maximum results (1-100) |

#### Return Type

```typescript
interface PharmacyInfo {
  // Identification
  pharmacy_id: string;          // Pharmacy ID
  name: string;                 // Pharmacy name

  // Address
  street: string | null;        // Street and number
  city: string;                 // City
  postal_code: string | null;   // Postal code
  district: string | null;      // District
  region: string | null;        // Region

  // Contact
  phone: string | null;         // Phone number
  email: string | null;         // Email
  web: string | null;           // Website

  // GPS coordinates
  latitude: number | null;      // Latitude
  longitude: number | null;     // Longitude

  // Operator
  operator: string | null;      // Pharmacy operator

  // Services
  has_24h_service: boolean;     // 24/7 service
  has_internet_sales: boolean;  // Online sales
  has_preparation_lab: boolean; // Pharmacy preparation lab

  // Status
  is_active: boolean;           // Active status
}
```

#### Examples

**Find pharmacies in Prague**:
```json
{
  "tool": "find_pharmacies",
  "params": {
    "city": "Praha",
    "limit": 10
  }
}
```

**Find 24/7 pharmacies**:
```json
{
  "tool": "find_pharmacies",
  "params": {
    "has_24h_service": true,
    "limit": 20
  }
}
```

**Find by postal code**:
```json
{
  "tool": "find_pharmacies",
  "params": {
    "postal_code": "11000",
    "limit": 5
  }
}
```

#### Current Limitations

**NOT IMPLEMENTED**: This tool currently returns an empty array because:
1. DLP dataset does not contain pharmacy data
2. Pharmacy data is in a separate SÚKL dataset

**Current Response**:
```json
[]
```

**Future Enhancement**: Load pharmacy data from:
- URL: https://opendata.sukl.cz/?q=katalog/seznam-lekaren
- Format: CSV with pharmacy registry

---

### 7. get_atc_info

Get information about ATC (Anatomical Therapeutic Chemical) classification.

**Location**: `/src/sukl_mcp/server.py` (lines 369-412)

#### Signature

```python
async def get_atc_info(atc_code: str) -> dict
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `atc_code` | string | Yes | ATC code (1-7 characters, e.g., 'N', 'N02', 'N02BE01') |

#### Return Type

```typescript
interface ATCInfo {
  code: string;                  // ATC code
  name: string;                  // ATC group name
  level: number;                 // Hierarchy level (1-5)
  children: ATCChild[];          // Child groups (max 20)
  total_children: number;        // Total number of children
}

interface ATCChild {
  code: string;                  // Child ATC code
  name: string;                  // Child name
}
```

#### ATC Classification Levels

| Level | Length | Description | Example |
|-------|--------|-------------|---------|
| 1 | 1 char | Anatomical main group | N (Nervous system) |
| 2 | 3 chars | Therapeutic subgroup | N02 (Analgesics) |
| 3 | 4 chars | Pharmacological subgroup | N02B (Other analgesics) |
| 4 | 5 chars | Chemical subgroup | N02BE (Anilides) |
| 5 | 7 chars | Chemical substance | N02BE01 (Paracetamol) |

#### Examples

**Level 1 - Main group**:
```json
{
  "tool": "get_atc_info",
  "params": {
    "atc_code": "N"
  }
}
```

**Response**:
```json
{
  "code": "N",
  "name": "Nervový systém",
  "level": 1,
  "children": [
    { "code": "N01", "name": "Anestetika" },
    { "code": "N02", "name": "Analgetika" },
    { "code": "N03", "name": "Antiepileptika" }
  ],
  "total_children": 8
}
```

**Level 3 - Pharmacological subgroup**:
```json
{
  "tool": "get_atc_info",
  "params": {
    "atc_code": "N02B"
  }
}
```

**Response**:
```json
{
  "code": "N02B",
  "name": "Jiná analgetika a antipyretika",
  "level": 3,
  "children": [
    { "code": "N02BA", "name": "Kyselina salicylová a deriváty" },
    { "code": "N02BB", "name": "Pyrazolony" },
    { "code": "N02BE", "name": "Anilidy" }
  ],
  "total_children": 3
}
```

**Level 5 - Chemical substance**:
```json
{
  "tool": "get_atc_info",
  "params": {
    "atc_code": "N02BE01"
  }
}
```

**Response**:
```json
{
  "code": "N02BE01",
  "name": "Paracetamol",
  "level": 5,
  "children": [],
  "total_children": 0
}
```

**Unknown ATC code**:
```json
{
  "code": "X99",
  "name": "Neznámá skupina",
  "level": 2,
  "children": [],
  "total_children": 0
}
```

#### Error Codes

| Error | Cause | HTTP Status |
|-------|-------|-------------|
| `SUKLValidationError` | ATC code length > 7 | 400 |

#### Data Source

ATC classifications from `dlp_atc.csv` (6,907 codes).

---

## Common Patterns

### Error Handling

All tools use consistent error handling:

```python
try:
    # Validation
    if not valid_input:
        raise SUKLValidationError("Description")

    # Processing
    result = await client.process(...)

    # Return
    return result

except SUKLValidationError as e:
    logger.warning(f"Validation error: {e}")
    raise  # FastMCP handles as 400-level error

except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise  # FastMCP handles as 500-level error
```

### Null Handling

Tools return `None` when entity not found:
- `get_medicine_details(invalid_code)` → `null`
- `get_pil_content(invalid_code)` → `null`
- `check_availability(invalid_code)` → `null`
- `get_reimbursement(invalid_code)` → `null`

Search tools return empty arrays:
- `search_medicine(no_matches)` → `{ results: [], total_results: 0 }`
- `find_pharmacies(no_matches)` → `[]`

### Async Patterns

All tools are async and use `await`:

```python
@mcp.tool
async def my_tool(param: str) -> Result:
    client = await get_sukl_client()  # Singleton
    data = await client.fetch_data(param)  # Async I/O
    return transform(data)
```

### Pydantic Validation

Return types are validated:

```python
# Automatic validation
result = MedicineDetail(
    sukl_code="0254045",
    name="PARALEN 500",
    # ... all required fields
)
# Raises pydantic.ValidationError if invalid

return result  # Serialized to JSON automatically
```

## MCP Protocol Details

### Request Format (JSON-RPC 2.0)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_medicine",
    "arguments": {
      "query": "ibuprofen",
      "limit": 10
    }
  }
}
```

### Response Format

**Success**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{...JSON response...}"
      }
    ]
  }
}
```

**Error**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "error": "SUKLValidationError: Query nesmí být prázdný"
    }
  }
}
```

### Tool Discovery

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "search_medicine",
        "description": "Vyhledá léčivé přípravky v databázi SÚKL...",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": { "type": "string" },
            "only_available": { "type": "boolean", "default": false },
            "only_reimbursed": { "type": "boolean", "default": false },
            "limit": { "type": "integer", "default": 20 }
          },
          "required": ["query"]
        }
      }
    ]
  }
}
```

## Performance Guidelines

### Response Time SLAs

| Tool | P50 | P95 | P99 |
|------|-----|-----|-----|
| `search_medicine` | 80ms | 200ms | 500ms |
| `get_medicine_details` | 10ms | 30ms | 100ms |
| `get_pil_content` | 15ms | 40ms | 120ms |
| `check_availability` | 15ms | 40ms | 120ms |
| `get_reimbursement` | 15ms | 40ms | 120ms |
| `find_pharmacies` | 5ms | 10ms | 20ms (empty) |
| `get_atc_info` | 50ms | 150ms | 400ms |

### Rate Limiting

**Current**: No rate limiting implemented

**Recommendation**:
- Per-client: 100 requests/minute
- Per-IP: 300 requests/minute
- Global: 1000 requests/minute

### Caching Strategy

**Current**: No caching (always fresh data)

**Future Enhancement**:
```python
# Redis-based caching
@cache(ttl=300)  # 5 minutes
async def get_medicine_details(sukl_code: str):
    ...
```

## Security Considerations

### Input Sanitization

All string inputs are sanitized:
1. Length limits enforced
2. Regex injection prevented (`regex=False`)
3. SQL injection not applicable (no SQL database)

### Authentication

**Current**: No authentication (public MCP server)

**Future**: Add API key authentication for HTTP transport:
```yaml
# smithery.yaml
environment:
  API_KEY: "{{ config.apiKey }}"
```

### HTTPS

**Current**: HTTP only for Smithery deployment

**Recommendation**: Add TLS termination:
- Use reverse proxy (nginx, Caddy)
- Smithery managed TLS
- Let's Encrypt certificates

---

**API Version**: 2.1.0
**Last Updated**: December 29, 2024
**Protocol**: Model Context Protocol (MCP)
