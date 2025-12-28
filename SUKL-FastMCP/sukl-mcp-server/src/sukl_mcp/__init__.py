"""
SÚKL MCP Server - FastMCP server pro přístup k databázi léčiv SÚKL.

Použití:
    from sukl_mcp import mcp
    
    # Spuštění serveru
    mcp.run()
"""

from .server import mcp
from .client import SUKLClient, SUKLConfig
from .models import (
    MedicineSearchResult,
    MedicineDetail,
    PharmacyInfo,
    AvailabilityInfo,
    ReimbursementInfo,
    PILContent
)

__version__ = "1.0.0"
__author__ = "AI Assistant"
__all__ = [
    "mcp",
    "SUKLClient",
    "SUKLConfig",
    "MedicineSearchResult",
    "MedicineDetail",
    "PharmacyInfo",
    "AvailabilityInfo",
    "ReimbursementInfo",
    "PILContent"
]
