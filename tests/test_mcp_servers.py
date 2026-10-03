# tests/test_mcp_servers.py
"""Tests for the MCP servers.

The @server.list_tools() / @server.call_tool() decorators return the original
functions, so the handlers are called directly — no stdio transport or subprocess.
"""
import json

import pytest

from src.database.db_manager import DatabaseManager
from src.mcp import database_server, hello_server

ROWS = [
    {"title": "GPT-5 launches", "url": "https://example.com/1", "source": "hackernews",
     "published_at": "2026-01-03", "summary": "New LLM"},
    {"title": "Rust release", "url": "https://example.com/2", "source": "rss",
     "published_at": "2026-01-02", "summary": "Systems language with ML crates"},
    {"title": "Weekend reading", "url": "https://example.com/3", "source": "rss",
     "published_at": "2026-01-01", "summary": "Assorted links"},
]


def _text(contents):
    [content] = contents
    assert content.type == "text"
    return content.text


async def _call_json(name, arguments):
    return json.loads(_text(await database_server.call_tool(name, arguments)))


@pytest.fixture
def mcp_db(tmp_path, monkeypatch):
    """Point the database server at a temp DB instead of data/news_agent.db."""
    db = DatabaseManager(str(tmp_path / "mcp.db"))
    monkeypatch.setattr(database_server, "db_manager", db)
    return db


async def _seed(db, rows=ROWS):
    await db.initialize()
    for row in rows:
        await db.insert_article(row)


# --- hello_server -----------------------------------------------------------


@pytest.mark.asyncio
async def test_hello_lists_tools():
    tools = await hello_server.list_tools()

    assert [t.name for t in tools] == ["greet", "add"]
    assert tools[0].inputSchema["required"] == ["name"]
    assert tools[1].inputSchema["required"] == ["a", "b"]


@pytest.mark.asyncio
async def test_hello_greet():
    assert _text(await hello_server.call_tool("greet", {"name": "Ada"})) == "Hello, Ada! 👋"


@pytest.mark.asyncio
async def test_hello_add():
    assert _text(await hello_server.call_tool("add", {"a": 2, "b": 3.5})) == "2 + 3.5 = 5.5"


@pytest.mark.asyncio
async def test_hello_unknown_tool():
    with pytest.raises(ValueError, match="Unknown tool"):
        await hello_server.call_tool("nope", {})


# --- database_server --------------------------------------------------------


@pytest.mark.asyncio
async def test_database_lists_tools():
    tools = await database_server.list_tools()

    assert [t.name for t in tools] == ["query_articles", "search_articles", "get_sources"]
    search = next(t for t in tools if t.name == "search_articles")
    assert search.inputSchema["required"] == ["query"]


@pytest.mark.asyncio
async def test_query_articles_filters_by_source(mcp_db):
    await _seed(mcp_db)

    data = await _call_json("query_articles", {"source": "rss"})

    assert data["total"] == 2
    assert {a["title"] for a in data["articles"]} == {"Rust release", "Weekend reading"}


@pytest.mark.asyncio
async def test_query_articles_returns_at_most_10_full_rows(mcp_db):
    rows = [{"title": f"A{i}", "url": f"https://example.com/{i}", "source": "rss",
             "published_at": f"2026-01-{i + 1:02d}"} for i in range(15)]
    await _seed(mcp_db, rows)

    data = await _call_json("query_articles", {})

    assert data["total"] == 15
    assert len(data["articles"]) == 10


@pytest.mark.asyncio
@pytest.mark.parametrize("query, expected_titles", [
    ("GPT", ["GPT-5 launches"]),   # title match, case-insensitive
    ("crates", ["Rust release"]),  # summary match
    ("quantum", []),
])
async def test_search_articles(mcp_db, query, expected_titles):
    await _seed(mcp_db)

    data = await _call_json("search_articles", {"query": query})

    assert data["query"] == query.lower()
    assert data["total"] == len(expected_titles)
    assert [a["title"] for a in data["articles"]] == expected_titles


@pytest.mark.asyncio
async def test_search_articles_respects_limit(mcp_db):
    await _seed(mcp_db)

    data = await _call_json("search_articles", {"query": "e", "limit": 2})

    assert data["total"] == 3  # total counts every match
    assert len(data["articles"]) == 2


@pytest.mark.asyncio
async def test_get_sources(mcp_db):
    await _seed(mcp_db)

    data = await _call_json("get_sources", {})

    assert sorted(data["sources"]) == ["hackernews", "rss"]
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_database_unknown_tool(mcp_db):
    await mcp_db.initialize()
    with pytest.raises(ValueError, match="Unknown tool"):
        await database_server.call_tool("drop_tables", {})


@pytest.mark.asyncio
async def test_call_tool_initializes_db_lazily(tmp_path, monkeypatch):
    monkeypatch.setattr(database_server, "db_manager", None)
    temp_db = DatabaseManager(str(tmp_path / "lazy.db"))

    async def fake_init_db():
        await temp_db.initialize()
        database_server.db_manager = temp_db

    monkeypatch.setattr(database_server, "init_db", fake_init_db)

    data = await _call_json("get_sources", {})

    assert data == {"sources": [], "total": 0}
    assert database_server.db_manager is temp_db
