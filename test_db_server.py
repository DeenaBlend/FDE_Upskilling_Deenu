"""Test database MCP server."""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_database_server():
    """Test database MCP server."""
    print("🔌 Connecting to database server...")
    
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src.mcp.database_server"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List tools
            tools = await session.list_tools()
            print(f"\n📋 Database tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # Get sources
            print(f"\n🔧 Getting sources...")
            result = await session.call_tool("get_sources", {})
            print(f"   {result.content[0].text[:200]}")
            
            # Query articles
            print(f"\n🔧 Querying articles...")
            result = await session.call_tool("query_articles", {"limit": 5})
            print(f"   {result.content[0].text[:300]}")
            
            # Search
            print(f"\n🔧 Searching for 'AI'...")
            result = await session.call_tool("search_articles", {
                "query": "AI",
                "limit": 3
            })
            print(f"   {result.content[0].text[:300]}")
            
            print("\n✅ Database MCP server working!")


if __name__ == "__main__":
    asyncio.run(test_database_server())