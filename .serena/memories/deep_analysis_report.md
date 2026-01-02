# Deep Codebase Analysis & FastMCP Validation Report

## 1. Critical Performance & Concurrency Issues

### 🔴 Blocking Event Loop in Fuzzy Search
**Location:** `src/sukl_mcp/fuzzy_search.py`
**Analysis:** The `FuzzyMatcher` uses `rapidfuzz.process.extract` and `fuzz.ratio`. These are CPU-intensive synchronous operations.
**Impact:** When a fuzzy search runs (which happens for every query that doesn't match exactly), the **entire server freezes**. No other requests (health checks, concurrent searches) can be processed.
**Fix:** Offload these calls to a thread pool using `asyncio.get_running_loop().run_in_executor()`.

### 🔴 "Cold Start" Latency
**Location:** `src/sukl_mcp/server.py` (Lifespan) & `src/sukl_mcp/client_csv.py`
**Analysis:**
- `server_lifespan` gets the client but only calls `health_check()`.
- `SUKLClient` loads data lazily in `search_medicines` via `await self.initialize()`.
**Impact:** The server starts quickly, but the **first user request hangs** for 10-30 seconds while 300MB of data is downloaded and parsed.
**Fix:** Explicitly call `await client.initialize()` inside `server_lifespan` to warm up the cache during startup.

### 🟠 Memory Inefficiency
**Location:** `src/sukl_mcp/client_csv.py`
**Analysis:** `pd.read_csv` uses standard NumPy object types for strings.
**Impact:** High memory usage (~1GB+) for 68k records with text descriptions.
**Fix:** Use `dtype_backend="pyarrow"` to reduce memory usage by ~40-50% and speed up string operations.

## 2. FastMCP Feature Validation

### ❌ Middleware (Missing)
**Status:** Critical Gap.
**Analysis:** The server lacks standard observability.
- No request logging (who asked what?).
- No standardized error handling (exceptions might leak internal details or look ugly to the LLM).
**Recommendation:** Add `ErrorHandlingMiddleware` and `LoggingMiddleware`.

### ❌ Context & Progress (Missing)
**Status:** High UX Impact.
**Analysis:** Long operations (data loading, PDF downloading) provide no feedback. The user just sees a "thinking..." spinner for too long.
**Recommendation:** Inject `ctx: Context` into `search_medicine` and `get_pil_content` to report progress (`ctx.report_progress`).

### ⚠️ Resources (Underutilized)
**Status:** Missed Opportunity.
**Analysis:** Static reference data (`dlp_atc`, `dlp_lecivelatky`) is hidden behind search tools.
**Recommendation:** Expose them as `sukl://atc-groups` and `sukl://substances` so agents can "read" the available categories.

### ⚠️ Dependency Injection (Legacy Pattern)
**Status:** Technical Debt.
**Analysis:** The project uses a global `_client` variable and a `get_sukl_client()` singleton function.
**Recommendation:** While functional, the "FastMCP way" is to use `Context` state or dependency injection, but given the size of the data, the Singleton is acceptable *if* initialized correctly in the lifespan.

## 3. Strategic Roadmap

1.  **Fix Concurrency**: Wrap fuzzy search in `run_in_executor`.
2.  **Fix Cold Start**: Move data loading to server startup.
3.  **Optimize Memory**: Switch to PyArrow.
4.  **Add Middleware**: Enable logging and error handling.
5.  **Enhance UX**: Add Progress Reporting via Context.
6.  **Expand API**: Add Resources for static data.
