"""
Test připojení k FastMCP dokumentačnímu serveru.
"""
import asyncio
from fastmcp import Client

async def main():
    async with Client("https://gofastmcp.com/mcp") as client:
        # Vyhledání informací o nasazení FastMCP serveru
        result = await client.call_tool(
            name="SearchFastMcp",
            arguments={"query": "how to deploy FastMCP server"}
        )
        print("=== Výsledek vyhledávání ===")
        print(result)

        # Zjištění dostupných nástrojů
        tools = await client.list_tools()
        print("\n=== Dostupné nástroje ===")
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")

if __name__ == "__main__":
    asyncio.run(main())
