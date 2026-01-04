# SÚKL MCP Server - Technical Documentation

## Overview

**SÚKL MCP Server** is a production-ready FastMCP server providing AI agents access to the Czech pharmaceutical database maintained by SÚKL (Státní ústav pro kontrolu léčiv / State Institute for Drug Control).

**Version:** 4.0.0
**Status:** Production Ready (REST API Migration Complete)
**Language:** Python 3.10+
**License:** MIT

## Key Statistics

- **68,248** registered medicines
- **787,877** composition records
- **3,352** active substances
- **6,907** ATC classification codes
- **61,240** documents (PIL/SPC)
- **7** MCP tools
- **241** comprehensive tests

## 🆕 What's New in v4.0.0

- **REST API Integration**: Hybrid architecture s REST API + CSV fallback
- **3 Tools Migrated**: search_medicine, get_medicine_details, check_availability
- **Performance Benchmarks**: Comprehensive performance testing suite
- **241 Tests**: 100% pass rate včetně integration a performance testů
- **Phase-01 Complete**: 75% REST API migration dokončena

See [Phase-01 Migration Plan](Phase-01-REST-API-Migration-Plan.md) for details.

## Documentation Structure

### For Developers

1. **[Architecture Documentation](architecture.md)**
   - System architecture diagrams
   - Component relationships
   - Data flow patterns
   - Security features

2. **[API Reference](api-reference.md)**
   - Complete MCP tools specification
   - Parameters and return types
   - Code examples
   - Error handling

3. **[Developer Guide](developer-guide.md)**
   - Development setup
   - Testing workflow
   - Code quality tools
   - Adding new features

### For Operations

4. **[Deployment Guide](deployment.md)**
   - FastMCP Cloud deployment
   - Smithery deployment
   - Docker containerization
   - Local development setup

5. **[Data Reference](data-reference.md)**
   - SÚKL Open Data structure
   - CSV file schemas
   - Data refresh strategy
   - Cache configuration

### For Users

6. **[User Guide](user-guide.md)**
   - Using with Claude Desktop
   - Configuration examples
   - Common use cases
   - Troubleshooting

7. **[Code Examples](examples.md)**
   - MCP tool usage examples
   - Python API integration
   - Error handling patterns
   - Best practices

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/DigiMedic/SUKL-mcp.git
cd SUKL-mcp

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# Install server
pip install -e ".[dev]"
```

### Run Server

```bash
# Local development (stdio transport)
python -m sukl_mcp

# Docker deployment (HTTP transport)
docker build -t sukl-mcp .
docker run -p 8000:8000 sukl-mcp
```

### Configure Claude Desktop

```json
{
  "mcpServers": {
    "sukl": {
      "command": "python",
      "args": ["-m", "sukl_mcp.server"],
      "env": {
        "PYTHONPATH": "/path/to/SUKL-mcp/src"
      }
    }
  }
}
```

## Architecture Highlights

### Multi-Layer Design

```
SÚKL Open Data → SUKLDataLoader → SUKLClient → FastMCP Server → AI Agents
                      ↓
                 REST API ← SUKLAPIClient (v4.0)
```

### Key Features

- **Hybrid Architecture (v4.0)**: REST API primary + CSV fallback pro 100% uptime
- **Async I/O**: Non-blocking ZIP extraction and CSV loading
- **Thread-Safe**: Race condition protection with asyncio.Lock
- **Security**: ZIP bomb protection, regex injection prevention
- **Type-Safe**: Pydantic 2.0 models with runtime validation
- **Configurable**: Environment variables for all settings

## Technology Stack

- **FastMCP 2.14+**: MCP protocol framework
- **Pydantic 2.0+**: Data validation and serialization
- **pandas 2.0+**: In-memory data processing
- **httpx**: Async HTTP client for data downloads
- **pytest**: Testing framework

## Data Source

All data sourced from official SÚKL Open Data portal:
- **URL**: https://opendata.sukl.cz
- **Update Frequency**: Monthly (typically around the 23rd)
- **Data Format**: CSV files in ZIP archive
- **Encoding**: Windows-1250 (cp1250)
- **License**: Open Data - free to use with attribution

## Legal Notice

This server provides information for informational purposes only. Always consult with healthcare professionals for medical advice. Data may be delayed and should not replace professional medical consultation.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

## Support

- **Issues**: https://github.com/DigiMedic/SUKL-mcp/issues
- **Discussions**: https://github.com/DigiMedic/SUKL-mcp/discussions
- **SÚKL Open Data**: https://opendata.sukl.cz

## License

MIT License - see [LICENSE](../LICENSE) file for details.

Data provided by SÚKL under Open Data terms: https://opendata.sukl.cz/?q=podminky-uziti

---

**Last Updated**: January 4, 2026
**Documentation Version**: 4.0.0
