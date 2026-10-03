# tests/test_search_skill.py
"""Tests for SearchSkill with the MCP client mocked (no server subprocess)."""
import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.skills.search_skill import SearchSkill


@contextmanager
def mcp_returns(payload=None, error=None):
    """Patch the stdio MCP client so `search_articles` returns `payload` or raises `error`."""
    with patch("src.skills.search_skill.stdio_client") as stdio_client, \
         patch("src.skills.search_skill.ClientSession") as client_session:
        stdio_client.return_value.__aenter__.return_value = (MagicMock(), MagicMock())
        session = client_session.return_value.__aenter__.return_value
        session.initialize = AsyncMock()
        if error is not None:
            session.call_tool = AsyncMock(side_effect=error)
        else:
            result = SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload))])
            session.call_tool = AsyncMock(return_value=result)
        yield SimpleNamespace(stdio_client=stdio_client, session=session)


def test_server_params_launch_database_server():
    params = SearchSkill().server_params
    assert params.command == "python"
    assert params.args == ["-m", "src.mcp.database_server"]


@pytest.mark.asyncio
async def test_search_returns_articles():
    skill = SearchSkill()
    articles = [{"title": "GPT-5 launches"}, {"title": "LLM roundup"}]

    with mcp_returns({"total": 2, "query": "llm", "articles": articles}) as mcp:
        result = await skill.search("llm", limit=5)

    assert result == {"success": True, "query": "llm", "total": 2, "articles": articles}
    mcp.stdio_client.assert_called_once_with(skill.server_params)
    mcp.session.initialize.assert_awaited_once()
    mcp.session.call_tool.assert_awaited_once_with(
        "search_articles", {"query": "llm", "limit": 5}
    )


@pytest.mark.asyncio
async def test_search_default_limit():
    with mcp_returns({"total": 0, "articles": []}) as mcp:
        await SearchSkill().search("anything")

    mcp.session.call_tool.assert_awaited_once_with(
        "search_articles", {"query": "anything", "limit": 10}
    )


@pytest.mark.asyncio
async def test_search_handles_tool_failure():
    with mcp_returns(error=RuntimeError("server crashed")):
        result = await SearchSkill().search("llm")

    assert result == {
        "success": False,
        "query": "llm",
        "error": "server crashed",
        "articles": [],
    }


@pytest.mark.asyncio
async def test_search_handles_malformed_payload():
    with mcp_returns({"unexpected": "shape"}):
        result = await SearchSkill().search("llm")

    assert result["success"] is False
    assert result["articles"] == []
