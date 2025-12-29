# SÚKL MCP Server Documentation

## Documentation Overview

This directory contains comprehensive technical documentation for the SÚKL MCP Server - a production-ready FastMCP server providing access to the Czech pharmaceutical database.

**Total Documentation**: 125+ pages across 8 documents
**Last Updated**: December 29, 2024
**Version**: 2.1.0

## Documentation Index

### 📘 [index.md](index.md) - Main Documentation Index
**4 pages** | Overview and navigation guide

- Quick start guide
- Key statistics (68,248 medicines, 7 MCP tools)
- Technology stack
- Project structure overview

**Start here** if you're new to the project.

---

### 🏗️ [architecture.md](architecture.md) - System Architecture
**25 pages** | Deep dive into system design

**Contents**:
- Multi-layer architecture diagrams (Mermaid)
- Component relationships and data flow
- Security features (ZIP bomb protection, regex injection prevention)
- Thread-safe singleton pattern with double-checked locking
- Performance benchmarks and scalability analysis
- Design decisions and rationale

**Key Topics**:
- SUKLDataLoader: Async data acquisition (15s download, 8s extraction, 8s CSV loading)
- SUKLClient: In-memory pandas DataFrame queries
- FastMCP Server: 7 MCP tools with Pydantic validation
- Deployment architectures (FastMCP Cloud vs Smithery)

**Read this** to understand the "why" behind architectural choices.

---

### 🔧 [api-reference.md](api-reference.md) - Complete API Documentation
**22 pages** | All 7 MCP tools with full specifications

**Tools Documented**:

1. **search_medicine** - Search medicines by name, substance, or ATC code
   - Parameters: query, only_available, only_reimbursed, limit
   - Returns: SearchResponse with medicines array
   - Typical latency: 50-150ms

2. **get_medicine_details** - Get comprehensive medicine information
   - Parameters: sukl_code (7 digits)
   - Returns: MedicineDetail with 27 fields
   - Typical latency: 5-20ms

3. **get_pil_content** - Get Patient Information Leaflet
   - Returns: PDF URL and metadata

4. **check_availability** - Check market availability
   - Returns: AvailabilityInfo with status

5. **get_reimbursement** - Get reimbursement information
   - Returns: ReimbursementInfo (limited data in v2.1.0)

6. **find_pharmacies** - Find pharmacies by criteria
   - Status: NOT IMPLEMENTED (returns empty array)

7. **get_atc_info** - Get ATC classification information
   - Returns: ATC hierarchy with children

**Includes**: Parameters, return types, examples, error codes, performance SLAs

**Use this** as the definitive API reference.

---

### 👨‍💻 [developer-guide.md](developer-guide.md) - Development Workflow
**17 pages** | Setup, testing, and contribution guide

**Contents**:
- Development environment setup (Python 3.10+, venv, pip)
- Project structure walkthrough
- Adding new MCP tools (step-by-step)
- Testing guide (pytest, 23 tests)
- Code quality tools (black, ruff, mypy)
- Debugging techniques (VS Code, pdb, logging)
- Performance profiling (cProfile, memory_profiler)
- CI/CD with GitHub Actions
- Makefile shortcuts

**Examples**:
- Creating new MCP tools with Pydantic models
- Writing comprehensive tests
- Using type hints and async patterns
- Environment variable configuration

**Read this** before contributing code.

---

### 🚀 [deployment.md](deployment.md) - Deployment Guide
**12 pages** | All deployment scenarios

**Deployment Modes**:

1. **Local Development** (stdio transport)
   - Claude Desktop integration
   - Configuration in `claude_desktop_config.json`
   - Virtual environment setup

2. **FastMCP Cloud** (stdio transport)
   - Managed cloud deployment
   - Auto-deploy from GitHub
   - Configuration via `fastmcp.yaml`
   - Commands: `fastmcp login`, `fastmcp deploy`

3. **Smithery** (HTTP transport)
   - Docker-based containerization
   - Configuration via `smithery.yaml`
   - Multi-stage Dockerfile (minimal image size)
   - Health checks and resource limits

**Includes**:
- Environment variables reference
- Performance tuning (memory, CPU)
- Security considerations (HTTPS, authentication, rate limiting)
- Monitoring and logging
- Troubleshooting guide
- Validation script

**Use this** for production deployments.

---

### 📊 [data-reference.md](data-reference.md) - Data Structure Documentation
**12 pages** | SÚKL Open Data detailed reference

**CSV Files Documented**:

1. **dlp_lecivepripravky.csv** (68,248 records)
   - Main medicines table
   - 20+ columns including name, strength, form, ATC, availability

2. **dlp_slozeni.csv** (787,877 records)
   - Medicine composition
   - Active ingredients and amounts

3. **dlp_lecivelatky.csv** (3,352 records)
   - Active pharmaceutical ingredients
   - CAS numbers and ATC codes

4. **dlp_atc.csv** (6,907 records)
   - ATC classification hierarchy
   - 5 levels from anatomical group to chemical substance

5. **dlp_nazvydokumentu.csv** (61,240 records)
   - Document references (PIL, SPC)

**Additional Files** (not currently loaded):
- dlp_cau_scau.csv - Pricing and reimbursement
- dlp_cau_scup.csv - Hospital pricing
- dlp_cau_sneh.csv - Non-reimbursed medicines

**Contents**:
- Complete column descriptions
- Data quality metrics (completeness, validation)
- Data loading process (download, extraction, CSV parsing)
- Refresh strategy (monthly updates from SÚKL)
- Legal and attribution requirements
- Performance characteristics (memory usage, query times)

**Use this** to understand the data structure and source.

---

### 📖 [user-guide.md](user-guide.md) - End-User Documentation
**12 pages** | For Claude Desktop and API users

**Contents**:

1. **Getting Started**
   - Quick start with Claude Desktop
   - Configuration examples
   - Verification steps

2. **Common Use Cases**
   - Medicine search (by name, substance, ATC code)
   - Availability checks
   - Getting patient information leaflets
   - Understanding ATC classification

3. **Understanding Results**
   - Search result format explanation
   - Medicine detail fields
   - ATC code hierarchy (5 levels)

4. **Tips and Best Practices**
   - Effective searching techniques
   - Understanding SÚKL codes
   - Interpreting availability and reimbursement
   - Patient safety disclaimers

5. **Troubleshooting**
   - Connection issues
   - No results found
   - Slow response times
   - Data freshness

6. **FAQs**
   - Update frequency
   - Data coverage
   - Privacy and data protection
   - Legal disclaimers

**Use this** for end-user guidance.

---

### 💡 [examples.md](examples.md) - Practical Code Examples
**21 pages** | 15 complete working examples

**Categories**:

1. **MCP Client Examples** (3 examples)
   - Basic JSON-RPC requests
   - Tool discovery
   - Medicine detail retrieval

2. **Python API Examples** (3 examples)
   - Direct SUKLClient usage
   - Pydantic models
   - ATC classification explorer

3. **Integration Examples** (3 examples)
   - Flask REST API wrapper
   - FastAPI modern wrapper
   - Streamlit dashboard

4. **Error Handling Examples** (2 examples)
   - Comprehensive exception handling
   - Retry logic with exponential backoff

5. **Performance Examples** (4 examples)
   - Batch processing with asyncio.gather
   - Caching wrapper with TTL
   - Performance monitoring
   - Memory profiling with tracemalloc

**Best Practices Section**:
- Always use async/await
- Handle errors gracefully
- Close resources properly
- Validate inputs
- Use type hints

**Use this** for implementation reference.

---

## Quick Navigation

### By Role

**Developers**:
1. Start: [index.md](index.md) → [developer-guide.md](developer-guide.md)
2. Code: [examples.md](examples.md)
3. Reference: [api-reference.md](api-reference.md)
4. Deep dive: [architecture.md](architecture.md)

**DevOps/SRE**:
1. Deploy: [deployment.md](deployment.md)
2. Monitor: [deployment.md#monitoring-and-logging](deployment.md#monitoring-and-logging)
3. Troubleshoot: [deployment.md#troubleshooting-guide](deployment.md#troubleshooting-guide)

**Data Engineers**:
1. Data: [data-reference.md](data-reference.md)
2. Performance: [architecture.md#performance-characteristics](architecture.md#performance-characteristics)
3. Optimization: [examples.md#performance-examples](examples.md#performance-examples)

**End Users**:
1. Setup: [user-guide.md](user-guide.md)
2. Usage: [user-guide.md#common-use-cases](user-guide.md#common-use-cases)
3. FAQ: [user-guide.md#frequently-asked-questions](user-guide.md#frequently-asked-questions)

**Architects**:
1. Overview: [architecture.md](architecture.md)
2. Design: [architecture.md#design-decisions-and-rationale](architecture.md#design-decisions-and-rationale)
3. Scaling: [architecture.md#scalability-considerations](architecture.md#scalability-considerations)

### By Task

**Setting up development environment**:
→ [developer-guide.md#development-environment-setup](developer-guide.md#development-environment-setup)

**Deploying to production**:
→ [deployment.md](deployment.md)

**Understanding data structure**:
→ [data-reference.md](data-reference.md)

**Adding new MCP tool**:
→ [developer-guide.md#adding-new-mcp-tools](developer-guide.md#adding-new-mcp-tools)

**Integrating with your app**:
→ [examples.md#integration-examples](examples.md#integration-examples)

**Troubleshooting issues**:
→ [deployment.md#troubleshooting-guide](deployment.md#troubleshooting-guide)

**Understanding architecture**:
→ [architecture.md](architecture.md)

## Documentation Statistics

| Document | Pages | Focus Area | Diagrams |
|----------|-------|------------|----------|
| index.md | 4 | Overview | 0 |
| architecture.md | 25 | System Design | 5 Mermaid |
| api-reference.md | 22 | API Specification | 0 |
| developer-guide.md | 17 | Development | 0 |
| deployment.md | 12 | Operations | 0 |
| data-reference.md | 12 | Data Structures | 1 |
| user-guide.md | 12 | End Users | 0 |
| examples.md | 21 | Code Examples | 0 |
| **Total** | **125+** | - | **6** |

## Documentation Features

- ✅ **Comprehensive**: Covers all aspects from architecture to usage
- ✅ **Practical**: 15 working code examples
- ✅ **Visual**: 6 Mermaid diagrams showing data flow and architecture
- ✅ **Searchable**: Markdown format with clear headings
- ✅ **Cross-referenced**: Internal links between documents
- ✅ **Versioned**: Dated with version numbers
- ✅ **Accurate**: Generated from actual source code
- ✅ **Complete**: API reference for all 7 MCP tools

## Contributing to Documentation

### Adding New Documentation

1. Create new `.md` file in `/docs` directory
2. Add entry to this README
3. Cross-reference from relevant documents
4. Update [index.md](index.md)

### Updating Existing Documentation

1. Update the `.md` file
2. Update "Last Updated" date
3. Increment version if major changes
4. Update changelog reference if applicable

### Documentation Style Guide

- Use clear, concise language
- Include code examples for complex topics
- Add diagrams for visual concepts (Mermaid preferred)
- Cross-reference related sections
- Include actual file paths and line numbers
- Use consistent terminology (see CLAUDE.md)

## Building Documentation

### Generate HTML (Optional)

```bash
# Using mkdocs
pip install mkdocs mkdocs-material
mkdocs build

# Using sphinx
pip install sphinx sphinx-rtd-theme
sphinx-build -b html docs/ docs/_build/
```

### Generate PDF (Optional)

```bash
# Using pandoc
pandoc docs/*.md -o SUKL-MCP-Server-Documentation.pdf

# Using mkdocs
mkdocs build
mkdocs-pdf-export-plugin
```

## Maintenance Schedule

- **Weekly**: Update API reference if tools change
- **Monthly**: Sync with SÚKL data updates
- **Per Release**: Update all version numbers and dates
- **As Needed**: Fix errors, add clarifications

## Feedback

Found an error or have suggestions?

- **GitHub Issues**: https://github.com/your-org/fastmcp-boilerplate/issues
- **Pull Requests**: https://github.com/your-org/fastmcp-boilerplate/pulls

---

**Documentation Generated**: December 29, 2024
**Project Version**: 2.1.0
**Python Version**: 3.10+
**Total Words**: ~50,000
**Total Pages**: 125+
