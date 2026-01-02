# SUKL MCP Server - Implementation Roadmap

Based on the comprehensive analysis of the codebase and FastMCP capabilities, here is the proposed roadmap for improving the project.

## Phase 1: Performance & Robustness (High Priority)
*Focus: Making the server faster, more memory-efficient, and easier to debug in production.*

1.  **Optimize Data Loading (PyArrow)**
    *   **Task**: Switch `pandas.read_csv` to use `dtype_backend="pyarrow"` and `engine="pyarrow"`.
    *   **Benefit**: Significant reduction in memory usage (strings are stored more efficiently) and faster filtering operations.
    *   **Files**: `src/sukl_mcp/client_csv.py`

2.  **Implement FastMCP Middleware**
    *   **Task**: Add `ErrorHandlingMiddleware` and `LoggingMiddleware` to the server instance.
    *   **Benefit**: Standardized error responses (including tracebacks for debugging) and consistent request logging.
    *   **Files**: `src/sukl_mcp/server.py`

## Phase 2: FastMCP Feature Completeness (Medium Priority)
*Focus: Utilizing the full potential of the FastMCP protocol.*

3.  **Expose Reference Data as Resources**
    *   **Task**: Create MCP Resources for static datasets that agents might want to read in full.
        *   `sukl://atc-groups`: List of all ATC codes and descriptions.
        *   `sukl://substances`: List of all active substances.
    *   **Benefit**: Allows agents to "browse" available categories without guessing search terms.
    *   **Files**: `src/sukl_mcp/server.py`

4.  **Add Utility Prompts**
    *   **Task**: Define standard prompts for common workflows.
        *   `find_substitutes`: Prompt to help find alternatives for a specific medicine.
        *   `explain_medicine`: Prompt to summarize medicine details for a patient.
    *   **Benefit**: Helps users/agents discover the server's capabilities and perform complex tasks more easily.
    *   **Files**: `src/sukl_mcp/server.py`

## Phase 3: Future Improvements (Low Priority)
*Focus: Advanced features and long-term maintenance.*

5.  **Vector Search Integration**
    *   **Task**: Replace or augment fuzzy search with vector embeddings (e.g., using `sqlite-vec` or similar lightweight solution).
    *   **Benefit**: Better semantic understanding (e.g., searching for "painkiller" finding "ibuprofen" even if the word isn't in the description).

6.  **Deployment Configuration**
    *   **Task**: Standardize the `main()` entry point to use FastMCP's built-in transport configuration if possible, or document the custom logic better.
