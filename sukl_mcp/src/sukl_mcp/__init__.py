"""
SÚKL MCP Server - Production-ready FastMCP server pro přístup k české databázi léčivých přípravků.

Poskytuje přístup k 68,248 léčivým přípravkům z SÚKL Open Data přes Model Context Protocol (MCP).
"""

from .client_csv import SUKLClient, SUKLConfig, get_sukl_client
from .exceptions import (
    SUKLDataError,
    SUKLException,
    SUKLValidationError,
    SUKLZipBombError,
)
from .models import (
    AvailabilityInfo,
    MedicineDetail,
    MedicineSearchResult,
    PharmacyInfo,
    PILContent,
    ReimbursementInfo,
    SearchResponse,
)
from .server import mcp

__version__ = "2.1.0"

__all__ = [
    # Server
    "mcp",
    # Client
    "SUKLClient",
    "SUKLConfig",
    "get_sukl_client",
    # Models
    "MedicineSearchResult",
    "MedicineDetail",
    "PharmacyInfo",
    "AvailabilityInfo",
    "ReimbursementInfo",
    "PILContent",
    "SearchResponse",
    # Exceptions
    "SUKLException",
    "SUKLValidationError",
    "SUKLZipBombError",
    "SUKLDataError",
]
