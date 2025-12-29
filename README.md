# SÚKL MCP Server

**Production-ready FastMCP server** poskytující přístup k české databázi léčivých přípravků SÚKL (68,248 přípravků).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.14+-green.svg)](https://gofastmcp.com)
[![Version](https://img.shields.io/badge/version-2.1.0-brightgreen.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-23%20passed-success.svg)](tests/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **v2.1.0** - Kompletně přepracovaný projekt s dual deployment (FastMCP Cloud + Smithery), 125+ stránek dokumentace. [Co je nového?](CHANGELOG.md)

## ⚡ Quick Start

```bash
# Instalace
pip install -e ".[dev]"

# Spuštění serveru
python -m sukl_mcp
```

## 📚 Documentation

**Kompletní dokumentace:** [docs/](docs/)

- **[Getting Started](docs/index.md)** - Rychlý úvod a instalace
- **[API Reference](docs/api-reference.md)** - Dokumentace všech 7 MCP tools
- **[Architecture](docs/architecture.md)** - Systémová architektura s diagramy
- **[Deployment](docs/deployment.md)** - FastMCP Cloud & Smithery deployment
- **[Developer Guide](docs/developer-guide.md)** - Vývojářský průvodce
- **[Examples](docs/examples.md)** - 15 příkladů použití
- **[Data Reference](docs/data-reference.md)** - SÚKL Open Data struktura
- **[User Guide](docs/user-guide.md)** - Uživatelská příručka

## ✨ Features

- **7 MCP tools** pro farmaceutická data (search, details, PIL, availability, reimbursement, pharmacies, ATC)
- **68,248 léčivých přípravků** z SÚKL Open Data
- **Async I/O** s pandas DataFrames pro rychlé vyhledávání
- **Dual deployment**: FastMCP Cloud (stdio) + Smithery (HTTP/Docker)
- **23 comprehensive tests** s pytest
- **Security features**: ZIP bomb protection, regex injection prevention
- **Type safety**: Pydantic modely s runtime validací

## 🚀 Deployment

### FastMCP Cloud

```bash
# Automatický deployment z GitHubu
# 1. Push do main branch
# 2. Připoj repo na https://fastmcp.cloud/
# 3. Server dostupný na: https://your-project.fastmcp.app/mcp
```

### Smithery

```bash
# Docker deployment
docker build -t sukl-mcp:2.1.0 .
smithery deploy
```

Detaily: [docs/deployment.md](docs/deployment.md)

## 📊 Data

- **68,248** registrovaných léčivých přípravků
- **787,877** záznamů složení
- **3,352** léčivých látek
- **6,907** ATC klasifikačních kódů
- **61,240** dokumentů (PIL/SPC)

*Data aktualizována: 23. prosince 2024*

## 🤝 Contributing

Viz [CONTRIBUTING.md](CONTRIBUTING.md) pro vývojářský workflow.

## 📄 License

MIT License - viz [LICENSE](LICENSE) soubor.

---

**Vytvořeno pomocí [FastMCP](https://gofastmcp.com)** | **Data od [SÚKL](https://opendata.sukl.cz)**
