# Data Reference

## SÚKL Open Data Overview

The SÚKL (Státní ústav pro kontrolu léčiv / State Institute for Drug Control) publishes comprehensive pharmaceutical data as Open Data.

**Source**: https://opendata.sukl.cz
**License**: Open Data - Free to use with attribution
**Update Frequency**: Monthly (typically around the 23rd)
**Format**: CSV files in ZIP archive
**Encoding**: Windows-1250 (cp1250)

## Current Dataset

**DLP (Database of Medicinal Products)**:
- **URL**: `https://opendata.sukl.cz/soubory/SOD20251223/DLP20251223.zip`
- **Size**: ~150 MB compressed, ~500 MB extracted
- **Last Updated**: December 23, 2024

## CSV Files Structure

### 1. dlp_lecivepripravky.csv

**Purpose**: Main table of registered medicinal products

**Records**: 68,248

**Key Columns**:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `KOD_SUKL` | Integer | SÚKL code (unique ID) | 254045 |
| `NAZEV` | String | Medicine name | PARALEN 500 |
| `DOPLNEK` | String | Name supplement | Zentiva |
| `SILA` | String | Strength | 500mg |
| `FORMA` | String | Pharmaceutical form | tableta |
| `BALENI` | String | Package size | 30 |
| `OBAL` | String | Package type | blistr |
| `CESTA` | String | Route of administration | perorální podání |
| `RC` | String | Registration number | 16/123/45-C |
| `REG` | String | Registration status | R (registered) |
| `DRZ` | String | Marketing authorization holder | Zentiva k.s. |
| `ATC_WHO` | String | ATC classification code | N02BE01 |
| `VYDEJ` | String | Dispensation mode | Rp (prescription) |
| `DODAVKY` | String | Availability | 1 (available) |
| `ZAV` | String | Narcotic substance | null |
| `DOPING` | String | Doping substance | null |

**Registration Status Codes**:
- `R` - Registered (Registrovaný)
- `B` - Cancelled (Zrušená registrace)
- `C` - Expired (Propadlá registrace)
- `P` - Parallel import (Souběžný dovoz)
- `D` - Parallel distribution (Souběžná distribuce)

**Dispensation Modes**:
- `Rp` - Prescription required (Na předpis)
- `Rp/o` - Restricted prescription (Na předpis s omezením)
- `F` - Over-the-counter (Volně prodejné)
- `Lp` - Pharmacy only (Pouze v lékárně)
- `V` - Reserved (Vyhrazené)

**Availability**:
- `1` - Available (Dodáván)
- `0` - Unavailable (Nedodáván)

### 2. dlp_slozeni.csv

**Purpose**: Composition of medicinal products

**Records**: 787,877

**Key Columns**:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `KOD_SUKL` | Integer | SÚKL code (FK to lecivepripravky) | 254045 |
| `ID_LATKY` | Integer | Substance ID (FK to lecivelatky) | 123 |
| `MNOZSTVI` | String | Amount of substance | 500 mg |
| `JEDNOTKA` | String | Unit | mg |

**Usage**:
- Join with `dlp_lecivepripravky` on `KOD_SUKL`
- Join with `dlp_lecivelatky` on `ID_LATKY`
- Get full composition for each medicine

### 3. dlp_lecivelatky.csv

**Purpose**: Active pharmaceutical ingredients

**Records**: 3,352

**Key Columns**:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `ID_LATKY` | Integer | Substance ID (unique) | 123 |
| `NAZEV` | String | Substance name (Czech) | Paracetamolum |
| `NAZEV_EN` | String | Substance name (English) | Paracetamol |
| `CAS` | String | CAS Registry Number | 103-90-2 |
| `ATC` | String | ATC code | N02BE01 |

**CAS Number**: Chemical Abstracts Service registry number for unique chemical identification

### 4. dlp_atc.csv

**Purpose**: ATC (Anatomical Therapeutic Chemical) classification

**Records**: 6,907

**Key Columns**:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `ATC` | String | ATC code (1-7 chars) | N02BE01 |
| `NAZEV` | String | ATC group name (Czech) | Paracetamol |
| `WHO` | String | WHO name (English) | Paracetamol |

**ATC Hierarchy**:

```
Level 1 (1 char):  N          - Nervous system
Level 2 (3 chars): N02        - Analgesics
Level 3 (4 chars): N02B       - Other analgesics and antipyretics
Level 4 (5 chars): N02BE      - Anilides
Level 5 (7 chars): N02BE01    - Paracetamol
```

### 5. dlp_nazvydokumentu.csv

**Purpose**: Document names (PIL, SPC)

**Records**: 61,240

**Key Columns**:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `KOD_SUKL` | Integer | SÚKL code (FK) | 254045 |
| `TYP_DOK` | String | Document type | PIL, SPC |
| `NAZEV_SOUBORU` | String | File name | 0254045_PIL.pdf |
| `PLATNOST_OD` | Date | Valid from | 2024-01-01 |

**Document Types**:
- `PIL` - Patient Information Leaflet (Příbalový leták)
- `SPC` - Summary of Product Characteristics (Souhrn údajů o přípravku)

## Additional CSV Files (Not Currently Loaded)

### dlp_cau_scau.csv

**Purpose**: Prices and reimbursements (ambulatory care)

**Records**: ~50,000

**Key Columns**:
- `KOD_SUKL` - SÚKL code
- `CAU` - Reimbursement category
- `VCP` - Maximum producer price
- `VLP` - Maximum retail price
- `VH` - Reimbursement amount
- `DO` - Patient copay

**Future Enhancement**: Load this file for complete reimbursement data

### dlp_cau_scup.csv

**Purpose**: Prices (hospital care)

**Records**: ~40,000

**Future Enhancement**: Add hospital pricing support

### dlp_cau_sneh.csv

**Purpose**: Non-reimbursed medicines

**Records**: ~20,000

**Future Enhancement**: Add to reimbursement detection

## Data Loading Process

### 1. Download

```python
async def _download_zip(zip_path: Path) -> None:
    """Download DLP ZIP from SÚKL Open Data."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream('GET', url) as resp:
            resp.raise_for_status()
            with open(zip_path, 'wb') as f:
                async for chunk in resp.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
```

**Performance**: ~15 seconds for 150 MB

### 2. Extraction

```python
async def _extract_zip(zip_path: Path) -> None:
    """Extract ZIP with bomb protection."""
    def _sync_extract():
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            total_size = sum(info.file_size for info in zip_ref.infolist())
            if total_size > 5 * 1024 * 1024 * 1024:  # 5 GB
                raise SUKLZipBombError(...)
            zip_ref.extractall(data_dir)

    await loop.run_in_executor(None, _sync_extract)
```

**Performance**: ~8 seconds
**Security**: ZIP bomb protection (max 5 GB)

### 3. CSV Loading

```python
async def _load_csvs() -> None:
    """Load CSV files in parallel."""
    def _load_single_csv(table: str) -> tuple[str, pd.DataFrame]:
        csv_path = data_dir / f"{table}.csv"
        df = pd.read_csv(csv_path, sep=';', encoding='cp1250', low_memory=False)
        return (table, df)

    results = await asyncio.gather(*[
        loop.run_in_executor(None, _load_single_csv, t)
        for t in tables
    ])
```

**Performance**: ~8 seconds (parallel) vs ~25 seconds (sequential)
**Memory**: ~300 MB for all DataFrames

## Data Quality

### Completeness

| Field | Completeness | Notes |
|-------|-------------|--------|
| `NAZEV` | 100% | Always present |
| `KOD_SUKL` | 100% | Unique identifier |
| `SILA` | 85% | Not all medicines have strength |
| `ATC_WHO` | 92% | Most have ATC classification |
| `DODAVKY` | 100% | Availability flag always present |
| `RC` | 95% | Registration number mostly present |

### Data Validation

**SÚKL Code**:
- Always numeric
- 1-7 digits
- Leading zeros stripped in CSV

**Dates**:
- Format: YYYY-MM-DD
- May be null for some fields

**Prices**:
- Decimal numbers
- Unit: CZK (Czech Koruna)

## Data Refresh Strategy

### Current Implementation

```python
# Static data - loaded once on startup
class SUKLDataLoader:
    def __init__(self):
        self._loaded = False

    async def load_data(self):
        if self._loaded:
            return  # No reload
        # ... load data
        self._loaded = True
```

**Pros**: Fast queries, no reloading overhead
**Cons**: Requires server restart for updates

### Future Enhancement: Auto-Refresh

```python
async def auto_refresh_worker():
    """Background worker to refresh data monthly."""
    while True:
        # Check for new data monthly
        await asyncio.sleep(30 * 24 * 3600)  # 30 days

        new_url = await check_latest_url()
        if new_url != current_url:
            logger.info(f"New data available: {new_url}")
            await reload_data(new_url)
```

## Data Usage Examples

### Search by Medicine Name

```python
# DataFrame query
df = loader.get_table('dlp_lecivepripravky')
results = df[df['NAZEV'].str.contains('PARALEN', case=False, na=False, regex=False)]

# Returns all medicines with "PARALEN" in name
```

### Get Medicine with Composition

```python
# Join medicines with composition
df_medicines = loader.get_table('dlp_lecivepripravky')
df_composition = loader.get_table('dlp_slozeni')
df_substances = loader.get_table('dlp_lecivelatky')

medicine = df_medicines[df_medicines['KOD_SUKL'] == 254045].iloc[0]
composition = df_composition[df_composition['KOD_SUKL'] == 254045]
substances = df_substances[df_substances['ID_LATKY'].isin(composition['ID_LATKY'])]

# Now you have medicine with all its active ingredients
```

### ATC Classification Tree

```python
# Get all ATC codes starting with "N02"
df_atc = loader.get_table('dlp_atc')
analgesics = df_atc[df_atc['ATC'].str.startswith('N02')]

# Build hierarchy
for code in analgesics['ATC']:
    level = len(code) if len(code) <= 5 else 5
    print(f"Level {level}: {code}")
```

## Data Dictionary

### Complete Field Mappings

**dlp_lecivepripravky.csv**:

```python
FIELD_MAPPINGS = {
    'KOD_SUKL': 'sukl_code',
    'NAZEV': 'name',
    'DOPLNEK': 'supplement',
    'SILA': 'strength',
    'FORMA': 'form',
    'BALENI': 'package',
    'OBAL': 'package_type',
    'CESTA': 'route',
    'RC': 'registration_number',
    'REG': 'registration_status',
    'DRZ': 'registration_holder',
    'ATC_WHO': 'atc_code',
    'VYDEJ': 'dispensation_mode',
    'DODAVKY': 'is_available',
    'ZAV': 'is_narcotic',
    'DOPING': 'is_doping',
}
```

## Legal and Attribution

### Data License

SÚKL Open Data Terms: https://opendata.sukl.cz/?q=podminky-uziti

**Permitted**:
- ✅ Free distribution and copying
- ✅ Commercial use
- ✅ Combination with other data
- ✅ Modification for technical reasons

**Required**:
- ⚠️ Attribution to SÚKL as source
- ⚠️ Link to https://opendata.sukl.cz

**Prohibited**:
- ❌ Altering the meaning of data
- ❌ Representing data as official SÚKL publications

### Attribution Template

```
Data source: SÚKL (Státní ústav pro kontrolu léčiv)
https://opendata.sukl.cz
Data version: DLP20251223
```

## Data Freshness

### Update Schedule

SÚKL publishes new data monthly, typically on the 23rd:

```
December 23, 2024: DLP20251223.zip
January 23, 2025:  DLP20250123.zip
February 23, 2025: DLP20250223.zip
...
```

### Checking for Updates

```python
import re
from datetime import datetime

def get_latest_url() -> str:
    """Construct URL for latest data."""
    today = datetime.now()
    month_code = f"SOD{today.year}{today.month:02d}23"
    file_code = f"DLP{today.year}{today.month:02d}23"
    return f"https://opendata.sukl.cz/soubory/{month_code}/{file_code}.zip"

# Check if exists
async def check_data_freshness():
    url = get_latest_url()
    async with httpx.AsyncClient() as client:
        resp = await client.head(url)
        return resp.status_code == 200
```

## Performance Characteristics

### Memory Usage by Table

| Table | Rows | Memory (MB) |
|-------|------|-------------|
| lecivepripravky | 68,248 | ~80 |
| slozeni | 787,877 | ~150 |
| lecivelatky | 3,352 | ~5 |
| atc | 6,907 | ~3 |
| nazvydokumentu | 61,240 | ~15 |
| **Total** | **927,624** | **~300** |

### Query Performance

| Operation | Complexity | Avg Time |
|-----------|-----------|----------|
| Search by name | O(n) - Full scan | 50-150ms |
| Get by SÚKL code | O(n) - Filter | 5-20ms |
| ATC lookup | O(n) - Filter | 30-80ms |

**Optimization Opportunity**: Add dict-based indexes:

```python
# Create index on startup
sukl_index = {
    row['KOD_SUKL']: idx
    for idx, row in df.iterrows()
}

# O(1) lookup
medicine = df.iloc[sukl_index[254045]]
```

---

**Last Updated**: December 29, 2024
**Data Version**: DLP20251223
**Total Records**: 927,624
