"""Shared pytest fixtures.

This file is automatically loaded by pytest. Add fixtures here as you build
out test coverage milestone by milestone (e.g. a `tmp_articles_dir` fixture
in M1, an `llm_response` fixture in M3, a `mcp_client` fixture in M4).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def llm_model(monkeypatch) -> str:
    """Configure a fake model name so agents can be built without a real .env."""
    monkeypatch.setenv("LITELLM_MODEL", "test-model")
    return "test-model"


@pytest.fixture
def llm_response():
    """Factory for fake LiteLLM `completion()` responses.

    Patch `src.agents.base_agent.completion` to return these, so no real LLM is called.
    """

    def make(content=None, tool_calls=None):
        message = MagicMock()
        message.content = content
        message.tool_calls = tool_calls
        message.model_dump.return_value = {"role": "assistant", "content": content}
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    return make


@pytest.fixture
def llm_tool_call():
    """Factory for one tool call as it appears on an LLM response message."""

    def make(name, arguments=None, call_id="call_1"):
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments or {})
        return SimpleNamespace(
            id=call_id, function=SimpleNamespace(name=name, arguments=arguments)
        )

    return make


@pytest.fixture
def sample_article_kwargs() -> dict:
    """Minimal kwargs for constructing an Article in tests.

    You'll define the Article dataclass in Milestone 1. Once it exists,
    tests can use this fixture to build instances without repeating boilerplate.
    """
    from datetime import datetime

    return {
        "title": "Sample article for tests",
        "url": "https://example.com/sample",
        "published_at": datetime(2026, 1, 1, 12, 0, 0),
        "source": "test",
    }
