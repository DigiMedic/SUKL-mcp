# Suggested Commands

## Setup and Installation
- **Install dependencies**: `make install` (runs `pip install -e ".[dev]"`)

## Development Workflow
- **Run Server**: `make run` (runs `python -m sukl_mcp`)
- **Run Tests**: `make test` (runs `pytest tests/ -v`)
- **Run Tests with Coverage**: `make test-cov`
- **Format Code**: `make format` (runs `black src/ tests/`)
- **Lint Code**: `make lint` (runs `ruff check src/` and `mypy src/sukl_mcp/`)
- **Clean Artifacts**: `make clean`
- **Full Dev Check**: `make dev` (runs format, test, and lint in sequence)

## System Utilities (macOS)
- **List files**: `ls -R`
- **Search text**: `grep -r "pattern" .`
- **Find files**: `find . -name "filename"`
