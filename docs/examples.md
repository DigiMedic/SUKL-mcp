# Code Examples

## Overview

This document provides practical code examples for using the SÚKL MCP Server programmatically, both as an MCP client and as a Python library.

## Table of Contents

1. [MCP Client Examples](#mcp-client-examples)
2. [Python API Examples](#python-api-examples)
3. [Integration Examples](#integration-examples)
4. [Error Handling Examples](#error-handling-examples)
5. [Performance Examples](#performance-examples)

---

## MCP Client Examples

### Example 1: Basic MCP Request (JSON-RPC)

```python
import httpx
import json

async def search_medicine_mcp(query: str, limit: int = 20):
    """Search medicines via MCP protocol."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/mcp",  # Smithery deployment
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "search_medicine",
                    "arguments": {
                        "query": query,
                        "limit": limit
                    }
                }
            },
            timeout=30.0
        )

        result = response.json()

        if "error" in result:
            raise Exception(f"MCP Error: {result['error']}")

        return json.loads(result["result"]["content"][0]["text"])

# Usage
import asyncio

results = asyncio.run(search_medicine_mcp("ibuprofen", limit=10))
print(f"Found {results['total_results']} medicines")
for med in results['results']:
    print(f"- {med['name']} ({med['sukl_code']})")
```

### Example 2: MCP Tool Discovery

```python
async def discover_tools():
    """Discover all available MCP tools."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
        )

        result = response.json()
        tools = result["result"]["tools"]

        for tool in tools:
            print(f"\nTool: {tool['name']}")
            print(f"Description: {tool['description']}")
            print(f"Parameters: {json.dumps(tool['inputSchema'], indent=2)}")

asyncio.run(discover_tools())
```

### Example 3: Get Medicine Details

```python
async def get_medicine_details_mcp(sukl_code: str):
    """Get detailed medicine information via MCP."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "get_medicine_details",
                    "arguments": {"sukl_code": sukl_code}
                }
            }
        )

        result = response.json()
        if "error" in result:
            return None

        return json.loads(result["result"]["content"][0]["text"])

# Usage
detail = asyncio.run(get_medicine_details_mcp("254045"))
if detail:
    print(f"Medicine: {detail['name']}")
    print(f"Strength: {detail['strength']}")
    print(f"Available: {detail['is_available']}")
```

---

## Python API Examples

### Example 4: Direct SUKLClient Usage

```python
from sukl_mcp.client_csv import SUKLClient
import asyncio

async def main():
    # Initialize client
    client = SUKLClient()
    await client.initialize()

    # Search medicines
    results = await client.search_medicines("paracetamol", limit=5)

    print(f"Found {len(results)} medicines:")
    for med in results:
        print(f"- {med['NAZEV']} (SÚKL: {med['KOD_SUKL']})")

    # Get specific medicine
    detail = await client.get_medicine_detail("254045")
    if detail:
        print(f"\nDetail for {detail['NAZEV']}:")
        print(f"  Strength: {detail.get('SILA', 'N/A')}")
        print(f"  Form: {detail.get('FORMA', 'N/A')}")
        print(f"  ATC: {detail.get('ATC_WHO', 'N/A')}")

    # Cleanup
    await client.close()

asyncio.run(main())
```

### Example 5: Using Pydantic Models

```python
from sukl_mcp.server import search_medicine, get_medicine_details
from sukl_mcp.models import SearchResponse, MedicineDetail
import asyncio

async def search_and_detail():
    # Search (returns Pydantic model)
    search_response: SearchResponse = await search_medicine(
        query="ibuprofen",
        only_available=True,
        limit=10
    )

    print(f"Search took {search_response.search_time_ms}ms")
    print(f"Found {search_response.total_results} results")

    # Get details for first result
    if search_response.results:
        first = search_response.results[0]
        detail: MedicineDetail | None = await get_medicine_details(first.sukl_code)

        if detail:
            # Type-safe access
            print(f"\nMedicine: {detail.name}")
            print(f"Registered: {detail.is_marketed}")
            print(f"Available: {detail.is_available}")

            # Optional fields
            if detail.atc_code:
                print(f"ATC: {detail.atc_code}")

asyncio.run(search_and_detail())
```

### Example 6: ATC Classification Explorer

```python
from sukl_mcp.server import get_atc_info
import asyncio

async def explore_atc_tree():
    """Explore ATC classification hierarchy."""

    # Start with main group
    level1 = await get_atc_info("N")
    print(f"Level 1: {level1['code']} - {level1['name']}")
    print(f"Children: {level1['total_children']}")

    # Explore first child (N02 - Analgesics)
    if level1['children']:
        child_code = level1['children'][0]['code']
        level2 = await get_atc_info(child_code)
        print(f"\nLevel 2: {level2['code']} - {level2['name']}")

        # Explore N02BE (Anilides)
        for child in level2['children']:
            if child['code'].startswith('N02BE'):
                level4 = await get_atc_info(child['code'])
                print(f"\nLevel 4: {level4['code']} - {level4['name']}")

                # Show substances
                for substance in level4['children'][:5]:
                    print(f"  - {substance['code']}: {substance['name']}")

asyncio.run(explore_atc_tree())
```

---

## Integration Examples

### Example 7: Flask REST API Wrapper

```python
from flask import Flask, jsonify, request
from sukl_mcp.server import search_medicine, get_medicine_details
import asyncio

app = Flask(__name__)

@app.route('/api/search', methods=['GET'])
def api_search():
    """REST API endpoint for medicine search."""
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 20))
    only_available = request.args.get('available', 'false').lower() == 'true'

    if not query:
        return jsonify({"error": "Query parameter 'q' required"}), 400

    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            search_medicine(query, only_available=only_available, limit=limit)
        )
        return jsonify(result.dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()

@app.route('/api/medicine/<sukl_code>', methods=['GET'])
def api_medicine_detail(sukl_code):
    """REST API endpoint for medicine details."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(get_medicine_details(sukl_code))
        if result is None:
            return jsonify({"error": "Medicine not found"}), 404
        return jsonify(result.dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        loop.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Example 8: FastAPI Modern Wrapper

```python
from fastapi import FastAPI, HTTPException, Query
from sukl_mcp.server import search_medicine, get_medicine_details
from sukl_mcp.models import SearchResponse, MedicineDetail

app = FastAPI(title="SÚKL API", version="1.0.0")

@app.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    available: bool = Query(False, description="Only available medicines"),
    reimbursed: bool = Query(False, description="Only reimbursed medicines")
):
    """Search for medicines."""
    try:
        return await search_medicine(
            query=q,
            only_available=available,
            only_reimbursed=reimbursed,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/medicine/{sukl_code}", response_model=MedicineDetail | None)
async def medicine_detail(sukl_code: str):
    """Get medicine details by SÚKL code."""
    result = await get_medicine_details(sukl_code)
    if result is None:
        raise HTTPException(status_code=404, detail="Medicine not found")
    return result

@app.get("/health")
async def health():
    """Health check endpoint."""
    from sukl_mcp.client_csv import get_sukl_client
    client = await get_sukl_client()
    return await client.health_check()

# Run with: uvicorn example:app --reload
```

### Example 9: Streamlit Dashboard

```python
import streamlit as st
from sukl_mcp.server import search_medicine, get_medicine_details
import asyncio

st.title("SÚKL Medicine Database")

# Search form
query = st.text_input("Search medicines", placeholder="Enter medicine name or substance")
only_available = st.checkbox("Only available medicines")
only_reimbursed = st.checkbox("Only reimbursed medicines")
limit = st.slider("Number of results", 1, 100, 20)

if st.button("Search") and query:
    with st.spinner("Searching..."):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                search_medicine(
                    query=query,
                    only_available=only_available,
                    only_reimbursed=only_reimbursed,
                    limit=limit
                )
            )

            st.success(f"Found {result.total_results} medicines in {result.search_time_ms:.0f}ms")

            for med in result.results:
                with st.expander(f"{med.name} - {med.sukl_code}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Strength**: {med.strength or 'N/A'}")
                        st.write(f"**Form**: {med.form or 'N/A'}")
                        st.write(f"**Package**: {med.package or 'N/A'}")

                    with col2:
                        st.write(f"**ATC**: {med.atc_code or 'N/A'}")
                        st.write(f"**Available**: {'✅' if med.is_available else '❌'}")
                        st.write(f"**Reimbursed**: {'✅' if med.has_reimbursement else '❌'}")

                    # Detail button
                    if st.button(f"Get Details", key=med.sukl_code):
                        detail = loop.run_until_complete(get_medicine_details(med.sukl_code))
                        if detail:
                            st.json(detail.dict())

        finally:
            loop.close()

# Run with: streamlit run example.py
```

---

## Error Handling Examples

### Example 10: Comprehensive Error Handling

```python
from sukl_mcp.client_csv import SUKLClient
from sukl_mcp.exceptions import (
    SUKLException,
    SUKLValidationError,
    SUKLZipBombError,
    SUKLDataError
)
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def robust_search(query: str):
    """Search with comprehensive error handling."""
    client = SUKLClient()

    try:
        # Initialize client
        await client.initialize()

        # Validate input
        if not query or len(query) > 200:
            raise ValueError("Query must be 1-200 characters")

        # Search medicines
        results = await client.search_medicines(query, limit=20)

        logger.info(f"Found {len(results)} results for '{query}'")
        return results

    except SUKLValidationError as e:
        logger.error(f"Validation error: {e}")
        return {"error": "invalid_input", "message": str(e)}

    except SUKLZipBombError as e:
        logger.critical(f"Security alert: {e}")
        return {"error": "security_error", "message": "Data file too large"}

    except SUKLDataError as e:
        logger.error(f"Data error: {e}")
        return {"error": "data_error", "message": "Failed to load data"}

    except SUKLException as e:
        logger.error(f"SÚKL error: {e}")
        return {"error": "sukl_error", "message": str(e)}

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return {"error": "internal_error", "message": "An unexpected error occurred"}

    finally:
        await client.close()

# Usage
result = asyncio.run(robust_search("ibuprofen"))
if isinstance(result, dict) and "error" in result:
    print(f"Error: {result['error']} - {result['message']}")
else:
    print(f"Success: {len(result)} results")
```

### Example 11: Retry Logic

```python
import asyncio
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

async def retry_async(
    func: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0
) -> Any:
    """Retry async function with exponential backoff."""
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                wait_time = delay * (backoff ** attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} attempts failed")

    raise last_exception

# Usage
from sukl_mcp.server import search_medicine

async def main():
    result = await retry_async(
        lambda: search_medicine("aspirin", limit=10),
        max_retries=3,
        delay=1.0
    )
    print(f"Found {result.total_results} results")

asyncio.run(main())
```

---

## Performance Examples

### Example 12: Batch Processing

```python
from sukl_mcp.server import get_medicine_details
import asyncio

async def batch_get_details(sukl_codes: list[str]):
    """Get details for multiple medicines in parallel."""
    # Create tasks for parallel execution
    tasks = [get_medicine_details(code) for code in sukl_codes]

    # Execute in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out None and exceptions
    valid_results = [
        r for r in results
        if r is not None and not isinstance(r, Exception)
    ]

    return valid_results

# Usage
codes = ["254045", "123456", "789012", "456789"]
details = asyncio.run(batch_get_details(codes))
print(f"Retrieved {len(details)} medicine details")
```

### Example 13: Caching Wrapper

```python
from functools import wraps
from typing import Any, Callable
import asyncio
import hashlib
import json
import time

class AsyncCache:
    """Simple async cache with TTL."""

    def __init__(self, ttl: float = 300.0):
        self.cache: dict[str, tuple[Any, float]] = {}
        self.ttl = ttl

    def _make_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function call."""
        key_data = {
            "func": func_name,
            "args": args,
            "kwargs": kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        """Cache value with current timestamp."""
        self.cache[key] = (value, time.time())

def cached(ttl: float = 300.0):
    """Decorator for caching async functions."""
    cache = AsyncCache(ttl)

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache._make_key(func.__name__, args, kwargs)

            # Check cache
            cached_value = cache.get(key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            cache.set(key, result)

            return result

        return wrapper
    return decorator

# Usage
from sukl_mcp.server import get_medicine_details

@cached(ttl=600.0)  # Cache for 10 minutes
async def cached_get_details(sukl_code: str):
    """Cached version of get_medicine_details."""
    return await get_medicine_details(sukl_code)

# First call - executes query
detail1 = asyncio.run(cached_get_details("254045"))

# Second call - returns cached result
detail2 = asyncio.run(cached_get_details("254045"))  # Fast!
```

### Example 14: Performance Monitoring

```python
import time
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def timer(operation: str) -> AsyncIterator[None]:
    """Context manager for timing async operations."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000  # ms
        logger.info(f"{operation} took {elapsed:.2f}ms")

# Usage
from sukl_mcp.server import search_medicine

async def monitored_search(query: str):
    """Search with performance monitoring."""
    async with timer(f"Search for '{query}'"):
        result = await search_medicine(query, limit=20)

    print(f"Found {result.total_results} results")
    print(f"Server reported: {result.search_time_ms:.2f}ms")

    return result

asyncio.run(monitored_search("ibuprofen"))
```

### Example 15: Memory Profiling

```python
import tracemalloc
import asyncio
from sukl_mcp.client_csv import SUKLClient

async def profile_memory():
    """Profile memory usage during data loading."""

    # Start tracing
    tracemalloc.start()

    # Take snapshot before
    snapshot1 = tracemalloc.take_snapshot()

    # Initialize client (loads data)
    client = SUKLClient()
    await client.initialize()

    # Take snapshot after
    snapshot2 = tracemalloc.take_snapshot()

    # Compare snapshots
    stats = snapshot2.compare_to(snapshot1, 'lineno')

    print("\n=== Top 10 Memory Increases ===")
    for stat in stats[:10]:
        print(f"{stat.size_diff / 1024 / 1024:.1f} MB - {stat.traceback}")

    # Current memory usage
    current, peak = tracemalloc.get_traced_memory()
    print(f"\nCurrent: {current / 1024 / 1024:.1f} MB")
    print(f"Peak: {peak / 1024 / 1024:.1f} MB")

    tracemalloc.stop()
    await client.close()

asyncio.run(profile_memory())
```

---

## Best Practices

### 1. Always Use Async/Await

```python
# ✅ Good - Uses async/await
async def good_example():
    result = await search_medicine("aspirin")
    return result

# ❌ Bad - Blocks event loop
def bad_example():
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(search_medicine("aspirin"))
    return result
```

### 2. Handle Errors Gracefully

```python
# ✅ Good - Catches specific exceptions
from sukl_mcp.exceptions import SUKLValidationError

try:
    result = await search_medicine("")
except SUKLValidationError as e:
    print(f"Invalid input: {e}")

# ❌ Bad - Catches all exceptions
try:
    result = await search_medicine("")
except:
    print("Something went wrong")
```

### 3. Close Resources

```python
# ✅ Good - Cleanup in finally
client = SUKLClient()
try:
    await client.initialize()
    # ... use client
finally:
    await client.close()

# ✅ Better - Use context manager
async with get_sukl_client() as client:
    # ... use client
```

### 4. Validate Inputs

```python
# ✅ Good - Validate before calling
def validate_sukl_code(code: str) -> bool:
    return code.isdigit() and 1 <= len(code) <= 7

sukl_code = input("Enter SÚKL code: ")
if validate_sukl_code(sukl_code):
    detail = await get_medicine_details(sukl_code)
else:
    print("Invalid SÚKL code")
```

### 5. Use Type Hints

```python
# ✅ Good - Clear types
async def search_by_name(name: str, limit: int = 20) -> list[dict]:
    client = await get_sukl_client()
    return await client.search_medicines(name, limit=limit)

# ❌ Bad - No types
async def search_by_name(name, limit=20):
    client = await get_sukl_client()
    return await client.search_medicines(name, limit=limit)
```

---

**Last Updated**: December 29, 2024
**Version**: 2.1.0
