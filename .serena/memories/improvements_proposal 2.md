# Improvement Proposal

Based on the analysis of the codebase and current best practices for FastMCP and Pandas, the following improvements are recommended:

## 1. Performance Optimization: PyArrow Backend for Pandas
**Current State:**
The project uses standard `pd.read_csv` with `low_memory=False`. This uses NumPy-backed arrays which can be memory-inefficient for string data (object dtype).

**Recommendation:**
Switch to `dtype_backend="pyarrow"` in `SUKLDataLoader._load_single_csv`.
**Benefits:**
- Significant memory reduction for string columns (which are the majority in SÚKL data).
- Faster string operations (filtering, searching).
- Better handling of missing values.

**Implementation:**
```python
df = pd.read_csv(
    csv_path, 
    sep=";", 
    encoding="cp1250", 
    dtype_backend="pyarrow", 
    engine="pyarrow"
)
```

## 2. Production Robustness: FastMCP Middleware
**Current State:**
The server uses basic logging and exception handling.

**Recommendation:**
Integrate FastMCP's built-in middleware stack.
**Benefits:**
- **ErrorHandlingMiddleware**: Standardized error responses and traceback management.
- **LoggingMiddleware**: Consistent request/response logging.
- **TimingMiddleware**: Performance monitoring for tool execution.

**Implementation:**
```python
from fastmcp.server.middleware import ErrorHandlingMiddleware, LoggingMiddleware

mcp.add_middleware(ErrorHandlingMiddleware())
mcp.add_middleware(LoggingMiddleware())
```

## 3. Search Optimization
**Current State:**
Fuzzy search uses `rapidfuzz` on the entire dataset or filtered subsets.

**Recommendation:**
Ensure `rapidfuzz` is used efficiently. If the dataset grows, consider pre-calculating or caching common fuzzy matches, or using vector search (though likely overkill for 68k records currently). The current multi-level pipeline is solid, but the PyArrow backend will speed up the exact and substring match phases.
