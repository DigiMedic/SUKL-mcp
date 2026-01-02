# Developer Guide

## Development Environment Setup

### Prerequisites

- **Python**: 3.10 or higher
- **pip**: Latest version
- **git**: For version control
- **Virtual environment**: venv or conda

### Initial Setup

```bash
# Clone repository
git clone https://github.com/DigiMedic/SUKL-mcp.git
cd SUKL-mcp

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Upgrade pip
pip install --upgrade pip

# Install package in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
python -m sukl_mcp --help
```

### Development Dependencies

```toml
# pyproject.toml [project.optional-dependencies]
dev = [
    "pytest>=8.0.0",           # Testing framework
    "pytest-asyncio>=0.23.0",  # Async test support
    "pytest-cov>=4.0.0",       # Coverage reporting
    "pytest-httpx>=0.30.0",    # HTTP mocking
    "black>=24.0.0",           # Code formatting
    "ruff>=0.3.0",             # Fast linting
    "mypy>=1.8.0",             # Type checking
]
```

## Project Structure

```
SUKL-mcp/
├── src/
│   └── sukl_mcp/
│       ├── __init__.py          # Package exports
│       ├── __main__.py          # Entry point (python -m sukl_mcp)
│       ├── server.py            # FastMCP server + 8 MCP tools
│       ├── client_csv.py        # Data loader + SÚKL client
│       ├── models.py            # Pydantic data models
│       ├── document_parser.py   # PDF/DOCX parser with LRU cache
│       ├── fuzzy_search.py      # Multi-level fuzzy search
│       ├── price_calculator.py  # Reimbursement calculations
│       └── exceptions.py        # Custom exceptions
│
├── tests/
│   ├── __init__.py
│   ├── test_validation.py       # Input validation tests
│   ├── test_async_io.py         # Async I/O tests
│   ├── test_availability.py     # Availability & alternatives tests
│   ├── test_document_parser.py  # Document parsing tests
│   ├── test_fuzzy_search.py     # Fuzzy search tests
│   └── test_price_calculator.py # Price calculation tests
│
├── docs/                        # Documentation (this folder)
│   ├── index.md
│   ├── architecture.md
│   ├── api-reference.md
│   ├── developer-guide.md
│   ├── deployment.md
│   ├── data-reference.md
│   ├── user-guide.md
│   └── examples.md
│
├── pyproject.toml               # Python project config
├── fastmcp.yaml                 # FastMCP Cloud config
├── smithery.yaml                # Smithery deployment config
├── Dockerfile                   # Docker container
├── README.md                    # User-facing README
├── CLAUDE.md                    # AI assistant instructions
├── CHANGELOG.md                 # Version history
├── LICENSE                      # MIT license
└── Makefile                     # Development shortcuts
```

## Development Workflow

### 1. Feature Development

```bash
# Create feature branch
git checkout -b feature/pharmacy-search

# Make changes to code
vim src/sukl_mcp/server.py

# Run tests frequently
pytest tests/ -v

# Format code
black src/

# Check linting
ruff check src/

# Type check
mypy src/

# Commit with conventional commit message
git commit -m "feat: add pharmacy search tool"

# Push to remote
git push origin feature/pharmacy-search
```

### 2. Testing Workflow

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_validation.py -v

# Run with coverage
pytest tests/ -v --cov=src/sukl_mcp --cov-report=term-missing

# Run with output capture disabled (see print statements)
pytest tests/ -v -s

# Run only tests matching pattern
pytest tests/ -v -k "test_search"

# Run with markers
pytest tests/ -v -m integration
```

### 3. Code Quality Workflow

```bash
# Format all Python code (automatic fixes)
black src/ tests/

# Check formatting without changes
black src/ tests/ --check

# Lint with ruff (fast)
ruff check src/ tests/

# Auto-fix linting issues
ruff check src/ tests/ --fix

# Type check with mypy
mypy src/

# Type check specific file
mypy src/sukl_mcp/server.py
```

## Adding New MCP Tools

### Step-by-Step Guide

#### 1. Define Pydantic Model

Add response model to `/src/sukl_mcp/models.py`:

```python
class NewToolResponse(BaseModel):
    """Response model for new_tool."""

    field1: str = Field(..., description="Description")
    field2: Optional[int] = Field(None, description="Optional field")
    timestamp: datetime = Field(default_factory=datetime.now)
```

Export in `__init__.py`:

```python
from .models import NewToolResponse

__all__ = [
    # ... existing exports
    "NewToolResponse",
]
```

#### 2. Add Client Method

Add data access method to `/src/sukl_mcp/client_csv.py`:

```python
class SUKLClient:
    # ... existing methods

    async def get_new_data(self, param: str) -> list[dict]:
        """Fetch new data from DataFrame."""
        # Input validation
        if not param or len(param) > 100:
            raise SUKLValidationError("Invalid param")

        if not self._initialized:
            await self.initialize()

        df = self._loader.get_table('table_name')
        if df is None:
            return []

        # Filter data
        results = df[df['COLUMN'].str.contains(param, regex=False, na=False)]

        # Return as dict records
        return results.to_dict('records')
```

#### 3. Create MCP Tool

Add tool to `/src/sukl_mcp/server.py`:

```python
@mcp.tool
async def new_tool(
    param: str,
    optional_param: bool = False,
    limit: int = 20,
) -> NewToolResponse:
    """
    Brief description of what the tool does.

    Longer description with usage examples.

    Args:
        param: Description of required parameter
        optional_param: Description of optional parameter
        limit: Maximum number of results

    Returns:
        NewToolResponse with results

    Examples:
        - new_tool("example")
        - new_tool("example", optional_param=True, limit=10)
    """
    client = await get_sukl_client()

    # Fetch data
    raw_data = await client.get_new_data(param)

    # Transform to Pydantic model
    results = []
    for item in raw_data[:limit]:
        try:
            results.append(
                NewToolResponse(
                    field1=item.get('FIELD1', ''),
                    field2=item.get('FIELD2'),
                )
            )
        except Exception as e:
            logger.warning(f"Error parsing item: {e}")

    return results
```

#### 4. Write Tests

Add tests to `/tests/test_new_tool.py`:

```python
import pytest
from sukl_mcp.server import new_tool
from sukl_mcp.exceptions import SUKLValidationError


@pytest.mark.asyncio
async def test_new_tool_basic():
    """Test basic new_tool functionality."""
    result = await new_tool("test")
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_new_tool_validation():
    """Test input validation."""
    with pytest.raises(SUKLValidationError):
        await new_tool("")  # Empty param

    with pytest.raises(SUKLValidationError):
        await new_tool("x" * 101)  # Too long


@pytest.mark.asyncio
async def test_new_tool_limit():
    """Test limit parameter."""
    result = await new_tool("test", limit=5)
    assert len(result) <= 5
```

#### 5. Update Documentation

Add tool to `/docs/api-reference.md`:

```markdown
### 8. new_tool

Brief description.

**Location**: `/src/sukl_mcp/server.py` (lines X-Y)

#### Signature
...

#### Parameters
...

#### Examples
...
```

### Best Practices for New Tools

1. **Always validate inputs** - Use SUKLValidationError for bad inputs
2. **Use async patterns** - All tools should be `async def`
3. **Return Pydantic models** - Never return raw dicts
4. **Handle errors gracefully** - Log warnings for partial failures
5. **Write comprehensive tests** - Test happy path, validation, and edge cases
6. **Document thoroughly** - Docstring becomes MCP tool description

## Testing Guide

### Test Structure

```python
# tests/test_example.py
import pytest
from sukl_mcp.server import search_medicine
from sukl_mcp.exceptions import SUKLValidationError


class TestSearchMedicine:
    """Test suite for search_medicine tool."""

    @pytest.mark.asyncio
    async def test_basic_search(self):
        """Test basic search functionality."""
        result = await search_medicine("test", limit=5)
        assert result.total_results <= 5
        assert all(isinstance(r.sukl_code, str) for r in result.results)

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Test that empty query raises validation error."""
        with pytest.raises(SUKLValidationError, match="prázdný"):
            await search_medicine("", limit=10)

    @pytest.mark.asyncio
    async def test_long_query(self):
        """Test that overly long query raises validation error."""
        with pytest.raises(SUKLValidationError, match="dlouhý"):
            await search_medicine("x" * 201, limit=10)

    @pytest.mark.asyncio
    async def test_limit_validation(self):
        """Test limit parameter validation."""
        with pytest.raises(SUKLValidationError):
            await search_medicine("test", limit=0)

        with pytest.raises(SUKLValidationError):
            await search_medicine("test", limit=101)
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_validation.py -v

# Specific test class
pytest tests/test_validation.py::TestSearchMedicine -v

# Specific test method
pytest tests/test_validation.py::TestSearchMedicine::test_basic_search -v

# With coverage
pytest tests/ -v --cov=src/sukl_mcp --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test Markers

```python
# Mark as integration test (requires network)
@pytest.mark.integration
async def test_download_data():
    """Test actual data download."""
    loader = SUKLDataLoader()
    await loader.load_data()
    assert loader._loaded

# Run only integration tests
# pytest tests/ -v -m integration

# Run only unit tests (exclude integration)
# pytest tests/ -v -m "not integration"
```

### Mocking External Dependencies

```python
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_search_with_mock():
    """Test search with mocked client."""
    mock_client = AsyncMock()
    mock_client.search_medicines.return_value = [
        {"KOD_SUKL": "12345", "NAZEV": "Test Medicine"}
    ]

    with patch('sukl_mcp.server.get_sukl_client', return_value=mock_client):
        result = await search_medicine("test")
        assert len(result.results) == 1
        assert result.results[0].name == "Test Medicine"
```

## Code Quality Tools

### Black (Code Formatter)

**Configuration** (`pyproject.toml`):
```toml
[tool.black]
line-length = 100
target-version = ["py310", "py311", "py312", "py313"]
```

**Usage**:
```bash
# Format all code
black src/ tests/

# Check formatting without changes
black src/ tests/ --check

# Show diff
black src/ tests/ --diff
```

**Pre-commit hook** (`.git/hooks/pre-commit`):
```bash
#!/bin/sh
black src/ tests/ --check || exit 1
```

### Ruff (Linter)

**Configuration** (`pyproject.toml`):
```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort (import sorting)
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by black)
]
```

**Usage**:
```bash
# Check all code
ruff check src/ tests/

# Auto-fix issues
ruff check src/ tests/ --fix

# Show all rules
ruff linter
```

### Mypy (Type Checker)

**Configuration** (`pyproject.toml`):
```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["httpx.*", "fastmcp.*"]
ignore_missing_imports = true
```

**Usage**:
```bash
# Check all code
mypy src/

# Check specific file
mypy src/sukl_mcp/server.py

# Generate HTML report
mypy src/ --html-report mypy-report/
```

**Common Type Hints**:
```python
from typing import Optional, List, Dict, Any

# Function with type hints
async def process(
    data: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Process data and return results."""
    results: List[Dict[str, Any]] = []
    # ... implementation
    return results

# Optional values
def get_detail(code: str) -> Optional[dict]:
    """Return detail or None if not found."""
    return detail or None
```

## Environment Variables

### Configuration

All configuration via environment variables:

```bash
# Data source
export SUKL_OPENDATA_URL="https://opendata.sukl.cz/soubory/SOD20251223/DLP20251223.zip"

# Local storage
export SUKL_CACHE_DIR="/var/cache/sukl"
export SUKL_DATA_DIR="/var/lib/sukl"

# Network
export SUKL_DOWNLOAD_TIMEOUT="120.0"  # seconds

# Transport (for deployment)
export MCP_TRANSPORT="stdio"  # or "http"
export MCP_HOST="0.0.0.0"
export MCP_PORT="8000"

# Logging
export LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
```

### .env File Support

Create `.env` file:
```bash
# .env
SUKL_CACHE_DIR=/tmp/sukl_cache
SUKL_DATA_DIR=/tmp/sukl_data
LOG_LEVEL=DEBUG
```

Load with python-dotenv:
```bash
pip install python-dotenv
```

```python
from dotenv import load_dotenv
load_dotenv()
```

## Debugging

### Local Debugging

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint() (Python 3.7+)
breakpoint()
```

### VS Code Debugging

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: SÚKL MCP Server",
      "type": "python",
      "request": "launch",
      "module": "sukl_mcp",
      "console": "integratedTerminal",
      "justMyCode": false,
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src",
        "LOG_LEVEL": "DEBUG"
      }
    },
    {
      "name": "Python: Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/", "-v", "-s"],
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

### Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Use in code
logger.debug("Detailed debug info")
logger.info("General info")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)  # Include stack trace
```

## Performance Profiling

### cProfile

```bash
# Profile entire server startup
python -m cProfile -o profile.stats -m sukl_mcp

# Analyze results
python -m pstats profile.stats
> sort cumulative
> stats 20
```

### Memory Profiling

```bash
pip install memory_profiler

# Add decorator to function
from memory_profiler import profile

@profile
async def load_data():
    # ... implementation

# Run with profiler
python -m memory_profiler src/sukl_mcp/client_csv.py
```

### Line Profiler

```bash
pip install line_profiler

# Add decorator
from line_profiler import profile

@profile
async def search_medicines(query: str):
    # ... implementation

# Run profiler
kernprof -l -v src/sukl_mcp/client_csv.py
```

## Continuous Integration

### GitHub Actions

`.github/workflows/test.yml`:
```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Lint with ruff
        run: ruff check src/ tests/

      - name: Format check with black
        run: black src/ tests/ --check

      - name: Type check with mypy
        run: mypy src/

      - name: Test with pytest
        run: pytest tests/ -v --cov=src/sukl_mcp --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Makefile Shortcuts

`Makefile`:
```makefile
.PHONY: install test lint format typecheck clean

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=src/sukl_mcp --cov-report=term-missing

lint:
	ruff check src/ tests/

format:
	black src/ tests/

typecheck:
	mypy src/

quality: format lint typecheck test

clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage coverage.xml

run:
	python -m sukl_mcp

docker-build:
	docker build -t sukl-mcp:latest .

docker-run:
	docker run -p 8000:8000 sukl-mcp:latest
```

**Usage**:
```bash
make install    # Install dependencies
make test       # Run tests
make quality    # Run all quality checks
make run        # Run server locally
```

## Contributing Guidelines

See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- Code style guide
- Commit message conventions
- Pull request process
- Code review checklist

## Troubleshooting

### Common Issues

**Issue**: `ImportError: No module named 'sukl_mcp'`

**Solution**:
```bash
# Ensure package installed in editable mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/SUKL-mcp/src"
```

**Issue**: `asyncio.Lock` error in tests

**Solution**:
```python
# Add to conftest.py
import pytest

@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

**Issue**: Pandas `DtypeWarning`

**Solution**:
```python
# Suppress warnings in tests
import warnings
warnings.filterwarnings('ignore', category=pd.errors.DtypeWarning)
```

---

**Last Updated**: December 29, 2024
**Version**: 2.1.0
