# Implementation Plan: SUKL-mcp Optimization

This plan consolidates findings from the codebase analysis and FastMCP validation.

## Phase 1: Performance & Core Stability (High Priority)
### 1.1 Optimize Data Loading with PyArrow
**Goal**: Reduce memory footprint and speed up data loading/filtering.
- **Action**: Update `SUKLDataLoader._load_single_csv` in `src/sukl_mcp/client_csv.py`.
- **Change**: Use `pd.read_csv(..., dtype_backend="pyarrow", engine="pyarrow")`.
- **Verification**: Check memory usage and startup time.

### 1.2 Integrate FastMCP Middleware
**Goal**: Standardize error handling and logging.
- **Action**: Update `src/sukl_mcp/server.py`.
- **Change**: Add `ErrorHandlingMiddleware` and `LoggingMiddleware`.
- **Benefit**: Better debugging info for the client (tracebacks, request logs).

## Phase 2: Enhanced User Experience (Medium Priority)
### 2.1 Progress Reporting via Context
**Goal**: Inform the user during long operations (e.g., initial data download).
- **Action**: Inject `ctx: Context` into `search_medicine` and potentially pass a callback to `SUKLDataLoader`.
- **Change**: Use `await ctx.report_progress(...)` during the ZIP download/extraction and CSV loading.

### 2.2 Expose Static Data as Resources
**Goal**: Allow agents to "browse" reference data without guessing.
- **Action**: Add `@mcp.resource` endpoints in `src/sukl_mcp/server.py`.
- **Resources**:
    - `sukl://atc-groups`: List of all ATC groups.
    - `sukl://substances`: List of active substances.

## Phase 3: Developer Experience (Low Priority)
### 3.1 Add Prompts
**Goal**: Help users/agents discover capabilities.
- **Action**: Add `@mcp.prompt` for common scenarios.
- **Prompts**:
    - `find_substitute`: "Find a substitute for [medicine] that is available."
    - `check_price`: "Check price and reimbursement for [medicine]."

### 3.2 Simplify Entry Point
**Goal**: Align with standard FastMCP patterns.
- **Action**: Refactor `main()` in `src/sukl_mcp/server.py` to rely more on FastMCP's internal transport handling if applicable, or clean up the manual env parsing.
