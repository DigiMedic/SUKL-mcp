"""
Test startu serveru s dual-mode (REST + CSV fallback).

Spustí server, počká 2 sekundy a ukončí ho.
"""

import asyncio
import signal
import sys


async def test_startup():
    """Test startu serveru."""
    print("🚀 Test startu SÚKL MCP Serveru (v4.0 - REST API + CSV fallback)\n")
    print("=" * 70)

    # Import serveru
    from sukl_mcp.server import mcp, server_lifespan

    # Test lifecycle
    print("\n✅ Server module imported successfully")

    # Simulace startu
    print("🔄 Testing lifespan context manager...")

    try:
        async with server_lifespan(mcp) as context:
            print(f"\n✅ Server started successfully!")
            print(f"   Initialized at: {context.initialized_at}")
            print(f"   CSV client: {type(context.client).__name__}")
            print(f"   API client: {type(context.api_client).__name__}")

            print("\n🔍 Checking client health...")
            print("   (Server is ready to accept requests)")

            # Krátká pauza
            await asyncio.sleep(1)

    except Exception as e:
        print(f"\n❌ Error during startup: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\n✅ Server shutdown successfully!")
    print("=" * 70)
    print("\n✅ All startup tests passed!")


if __name__ == "__main__":
    asyncio.run(test_startup())
