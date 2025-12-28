"""SÚKL MCP Server - FastMCP server pro přístup k databázi léčiv."""

from .client import SUKLClient, SUKLConfig
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

__version__ = "1.0.0"

__all__ = [
    "mcp",
    "SUKLClient",
    "SUKLConfig",
    "MedicineSearchResult",
    "MedicineDetail",
    "PharmacyInfo",
    "AvailabilityInfo",
    "ReimbursementInfo",
    "PILContent",
    "SearchResponse",
]
