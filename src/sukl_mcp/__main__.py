"""
Entry point pro spuštění SÚKL MCP serveru.

Použití:
    python -m sukl_mcp
"""

if __name__ == "__main__":
    # Import absolutní cesty pro FastMCP Cloud compatibility
    from sukl_mcp.server import mcp

    # Spuštění serveru
    mcp.run()
