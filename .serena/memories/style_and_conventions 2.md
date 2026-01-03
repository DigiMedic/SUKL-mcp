# Style and Conventions

## Code Style
- **Formatter**: `black` is the authoritative code formatter. All code must be formatted with it.
- **Linter**: `ruff` is used for linting. Ensure no errors are reported.
- **Type Checking**: `mypy` is used for static type checking. The project is fully typed (`Typing :: Typed`).

## Naming Conventions
- **Python**: Follows standard PEP 8 conventions (snake_case for functions/variables, PascalCase for classes).
- **Directories**: `src/sukl_mcp` for source code, `tests/` for tests.

## Documentation
- **Docstrings**: Use docstrings for modules, classes, and functions.
- **Language**: The project documentation (README) is in Czech, but code comments and docstrings may be in English or Czech (check existing files for consistency). Based on `__main__.py`, docstrings seem to be in Czech.

## Testing
- **Framework**: `pytest`.
- **Coverage**: Aim for high test coverage (>85%).
- **Location**: All tests should be placed in the `tests/` directory.

## Framework Specifics
- **FastMCP**: Use FastMCP decorators and patterns for defining tools and resources.
- **Pydantic**: Use Pydantic v2 models for data validation and schema definition.
