# User Guide

## Introduction

The SÚKL MCP Server provides AI agents like Claude with access to the Czech pharmaceutical database containing information about 68,248 registered medicines, their composition, availability, and reimbursement status.

## Getting Started

### Prerequisites

- **Claude Desktop** (recommended) or any MCP-compatible client
- **Python 3.10+** installed on your system
- **Internet connection** (for initial data download)

### Quick Start with Claude Desktop

#### 1. Install Server

```bash
# macOS/Linux
cd ~/Documents
git clone https://github.com/DigiMedic/SUKL-mcp.git
cd SUKL-mcp
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

#### 2. Configure Claude Desktop

Edit configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Linux**: `~/.config/Claude/claude_desktop_config.json`

Add server configuration:

```json
{
  "mcpServers": {
    "sukl": {
      "command": "python",
      "args": ["-m", "sukl_mcp.server"],
      "env": {
        "PYTHONPATH": "/Users/yourname/Documents/SUKL-mcp/src"
      }
    }
  }
}
```

Replace `/Users/yourname/Documents/SUKL-mcp/src` with your actual path.

#### 3. Restart Claude Desktop

Close and reopen Claude Desktop for changes to take effect.

#### 4. Verify Connection

In Claude, try asking:

```
Can you search for medicines containing ibuprofen in the SÚKL database?
```

You should see results from the Czech pharmaceutical database.

## Common Use Cases

### 1. Medicine Search

**Find medicines by name**:
```
Show me all medicines with "Paralen" in the name
```

**Find by active substance**:
```
Search for medicines containing paracetamol
```

**Find by ATC code**:
```
Find all analgesics (ATC code N02)
```

**Filter available medicines**:
```
Search for ibuprofen medicines that are currently available on the market
```

**Filter reimbursed medicines**:
```
Find reimbursed medicines containing aspirin
```

### 2. Medicine Details

**Get complete information**:
```
Get detailed information about medicine with SÚKL code 254045
```

**Check multiple aspects**:
```
For SÚKL code 254045, show me:
- Full name and strength
- Registration status
- Availability
- Reimbursement information
```

### 3. Availability Checks

**Check single medicine**:
```
Is medicine 254045 currently available on the Czech market?
```

**Compare availability**:
```
Check availability for these SÚKL codes: 254045, 123456, 789012
```

### 4. Patient Information

**Get PIL (Patient Information Leaflet)**:
```
Get the patient information leaflet for SÚKL code 254045
```

**Safety information**:
```
For medicine 254045, is it a narcotic or doping substance?
```

### 5. ATC Classification

**Understand drug categories**:
```
What is ATC code N02?
```

**Browse hierarchy**:
```
Show me all subgroups under ATC code N02
```

**Find specific substance**:
```
What is ATC code N02BE01?
```

## Understanding Results

### Search Results Format

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

**Key Fields**:
- `sukl_code`: Unique 7-digit identifier for the medicine
- `name`: Official medicine name
- `supplement`: Additional name information (e.g., manufacturer)
- `strength`: Dosage strength (e.g., "500mg")
- `form`: Pharmaceutical form (e.g., "tableta", "sirup")
- `package`: Package size (e.g., "30" tablets)
- `atc_code`: ATC classification (see ATC Guide below)
- `registration_status`: R=Registered, B=Cancelled, C=Expired
- `dispensation_mode`: Rp=Prescription, F=OTC, Lp=Pharmacy only
- `is_available`: Currently available on market
- `has_reimbursement`: Reimbursed by health insurance

### Medicine Detail Format

Includes all search fields plus:

- `route`: Route of administration (e.g., "perorální podání")
- `package_type`: Type of packaging (e.g., "blistr")
- `registration_number`: Official registration number
- `registration_holder`: Marketing authorization holder
- `is_narcotic`: Whether medicine contains narcotic substances
- `is_doping`: Whether medicine is on doping list

### ATC Codes Explained

ATC (Anatomical Therapeutic Chemical) classification organizes medicines by:

**Level 1** (1 char): Anatomical main group
- A: Alimentary tract and metabolism
- B: Blood and blood forming organs
- C: Cardiovascular system
- D: Dermatologicals
- **N: Nervous system**
- ...

**Level 2** (3 chars): Therapeutic subgroup
- N01: Anesthetics
- **N02: Analgesics**
- N03: Antiepileptics

**Level 3** (4 chars): Pharmacological subgroup
- N02A: Opioids
- **N02B: Other analgesics and antipyretics**

**Level 4** (5 chars): Chemical subgroup
- N02BA: Salicylic acid derivatives
- **N02BE: Anilides**

**Level 5** (7 chars): Chemical substance
- **N02BE01: Paracetamol**

## Tips and Best Practices

### 1. Effective Searching

**Use partial names**:
```
✅ "Paralen" finds PARALEN 500, PARALEN GRIP, etc.
❌ "PARALEN 500mg tableta" might miss variations
```

**Search by active substance**:
```
✅ "paracetamol" finds all paracetamol-containing medicines
✅ "ibuprofen" finds all ibuprofen products
```

**Use ATC codes for categories**:
```
✅ "N02" finds all analgesics
✅ "M01AE" finds all propionic acid derivatives
```

### 2. Understanding SÚKL Codes

SÚKL codes are unique identifiers:
- **Format**: 7 digits (e.g., 0254045)
- **Leading zeros**: Optional (254045 = 0254045)
- **Uniqueness**: Each code identifies exactly one medicine
- **Stability**: Codes don't change even if medicine details update

### 3. Interpreting Availability

**is_available = true**:
- Medicine is being supplied to market
- Available in pharmacies

**is_available = false**:
- Temporarily out of stock, or
- Permanently discontinued
- Check `unavailability_reason` for details

### 4. Understanding Reimbursement

**Current Limitation**: Detailed reimbursement data is limited in v2.1.0

**What's Available**:
- Basic reimbursement flag (yes/no)
- Medicine name and SÚKL code

**What's Coming**:
- Exact reimbursement amounts
- Patient copay calculations
- Reimbursement groups (CAU)
- Indication limitations

**Workaround**: For detailed pricing, visit https://www.sukl.cz

### 5. Patient Safety

**IMPORTANT DISCLAIMERS**:
- Information is for informational purposes only
- Always consult healthcare professionals
- Follow your doctor's prescriptions
- Data may be delayed (monthly updates)
- Not a substitute for medical advice

## Troubleshooting

### "No connection to SÚKL server"

**Cause**: Claude Desktop can't reach the MCP server

**Solutions**:
1. Verify server is configured in `claude_desktop_config.json`
2. Check PYTHONPATH is absolute path, not relative
3. Ensure virtual environment is activated when testing manually:
   ```bash
   source venv/bin/activate
   python -m sukl_mcp.server
   ```
4. Restart Claude Desktop after config changes

### "No results found"

**Cause**: Search query doesn't match any medicines

**Solutions**:
1. Try shorter search terms (e.g., "aspirin" instead of "aspirin 100mg")
2. Check spelling (Czech names may differ from English)
3. Try searching by active substance instead of brand name
4. Use ATC code for broader category search

### "Medicine not found for SÚKL code"

**Cause**: Invalid or non-existent SÚKL code

**Solutions**:
1. Verify SÚKL code is correct (7 digits)
2. Check if medicine is still registered (may be cancelled)
3. Try searching by name to find current SÚKL code

### Slow Response Times

**Cause**: First-time data loading or large result sets

**Solutions**:
1. First query after server start is slower (~30s) due to data loading
2. Subsequent queries are fast (<1s)
3. Reduce result limit for faster responses:
   ```
   Search for "aspirin" with maximum 10 results
   ```

### "Data seems outdated"

**Cause**: SÚKL updates data monthly

**Solutions**:
1. Check last data update: Data version DLP20251223 = December 23, 2024
2. For latest info, visit official SÚKL website: https://www.sukl.cz
3. To refresh server data:
   ```bash
   # Delete cache and restart
   rm -rf /tmp/sukl_dlp_cache /tmp/sukl_dlp_data
   # Restart Claude Desktop
   ```

## Advanced Usage

### Combining Multiple Queries

**Find alternatives**:
```
1. Search for medicines containing paracetamol
2. For each result, check availability
3. Show me only available medicines
```

**Compare medicines**:
```
Compare these medicines:
- SÚKL 254045
- SÚKL 123456
Show me their strength, form, and availability
```

### Batch Operations

**Check multiple codes**:
```
Check availability for SÚKL codes: 254045, 123456, 789012, 456789
```

**Search multiple substances**:
```
Find medicines for each of these substances:
- Paracetamol
- Ibuprofen
- Aspirin
Limit to 5 results each
```

### Filtering and Sorting

**Available only**:
```
Search for "vitamin" but show only available medicines
```

**Reimbursed only**:
```
Find all ibuprofen medicines that are reimbursed by health insurance
```

**By package size**:
```
Find paracetamol medicines and tell me which have the largest package size
```

## Frequently Asked Questions

### Q: How often is data updated?

**A**: SÚKL publishes new data monthly (typically on the 23rd). The server must be restarted to load new data.

### Q: Can I get information about veterinary medicines?

**A**: No, this server only includes human medicines (DLP dataset). Veterinary medicines are in a separate SÚKL dataset.

### Q: Why can't I find information about pharmacies?

**A**: Pharmacy search is not yet implemented (v2.1.0). This will be added in a future update.

### Q: Are medicine prices included?

**A**: Basic pricing data is limited. Full pricing and reimbursement details will be added in a future version.

### Q: Can I use this for prescription decisions?

**A**: NO. This is informational only. Always consult your doctor or pharmacist for prescription decisions.

### Q: Is data from SÚKL official?

**A**: Yes, all data comes from official SÚKL Open Data portal (https://opendata.sukl.cz). However:
- Data may be delayed (monthly updates)
- Always verify critical information on official SÚKL website
- Not a substitute for official SÚKL publications

### Q: Can I search in English?

**A**: Medicine names are in Czech, but you can search using international substance names (e.g., "paracetamol", "ibuprofen"). ATC codes are international.

### Q: What if a medicine has multiple strengths?

**A**: Each strength is a separate record with its own SÚKL code. Search will return all variants.

Example:
- PARALEN 500: SÚKL code 0254045
- PARALEN 250: SÚKL code 0123456 (different code)

## Privacy and Data Protection

### What Data is Collected?

**Server-side**:
- No personal data collected
- No search history stored
- No user tracking

**Claude Desktop**:
- Conversation history stored locally by Claude app
- Subject to Claude's privacy policy

### Is My Search History Private?

**Yes**:
- Server doesn't log search queries
- No analytics or tracking
- Each query is processed independently

### Can Others See My Searches?

**No**:
- Local deployment = completely private
- No data sent to third parties
- SÚKL data is public information

## Legal Disclaimer

**IMPORTANT NOTICE**:

1. This service provides **informational content only**
2. **Not a substitute** for professional medical advice
3. Always **consult healthcare professionals** for:
   - Prescription decisions
   - Dosage information
   - Drug interactions
   - Medical conditions

4. Data accuracy:
   - Sourced from official SÚKL Open Data
   - May be delayed (monthly updates)
   - Verify critical information on https://www.sukl.cz

5. No liability:
   - Service provided "as is"
   - No warranty of accuracy or completeness
   - Use at your own risk

## Getting Help

### Report Issues

GitHub Issues: https://github.com/DigiMedic/SUKL-mcp/issues

### Documentation

- [API Reference](api-reference.md) - Complete tool documentation
- [Examples](examples.md) - Code examples
- [Deployment Guide](deployment.md) - Setup instructions

### Official Resources

- **SÚKL Website**: https://www.sukl.cz
- **SÚKL Open Data**: https://opendata.sukl.cz
- **MCP Specification**: https://modelcontextprotocol.io

---

**Last Updated**: December 29, 2024
**Version**: 2.1.0
**Data Version**: DLP20251223
