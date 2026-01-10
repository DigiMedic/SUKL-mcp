"""
SÚKL API modul - Unified REST API klient pro SÚKL databáze.

Tento modul poskytuje:
- SUKLAPIClient: Hlavní async klient pro komunikaci s SÚKL REST API
- Modely pro API responses
- Caching a retry logiku

Použití:
    from sukl_mcp.api import SUKLAPIClient

    async with SUKLAPIClient() as client:
        medicines = await client.search_medicines("ibuprofen")
        detail = await client.get_medicine("0254045")
"""

from sukl_mcp.api.client import (
    SUKLAPIClient,
    SUKLAPIConfig,
    close_rest_client,
    get_rest_client,
)
from sukl_mcp.api.models import (
    APICena,
    APILecivyPripravek,
    APISearchResponse,
    APIUhrada,
)

__all__ = [
    "SUKLAPIClient",
    "SUKLAPIConfig",
    "get_rest_client",
    "close_rest_client",
    "APILecivyPripravek",
    "APISearchResponse",
    "APICena",
    "APIUhrada",
]
