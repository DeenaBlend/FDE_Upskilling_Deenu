# tests/test_enhanced_filter_agent.py
"""Offline tests for EnhancedFilterAgent's tool wiring and judgment parsing."""
import json
from unittest.mock import patch

import pytest

from src.agents.enhanced_filter_agent import EnhancedFilterAgent
from src.agents.news_filter_agent import NewsFilterAgent
from src.tools.calculator import CALCULATOR_SCHEMA, calculator
from src.tools.web_search import WEB_SEARCH_SCHEMA, web_search

JUDGMENT = {
    "relevant": True,
    "relevance_score": 8,
    "reasoning": "Used calculator",
    "key_topics": ["LLM"],
}


@pytest.fixture
def agent(llm_model):
    return EnhancedFilterAgent()


def test_registers_tool_schemas_and_functions(agent):
    assert isinstance(agent, NewsFilterAgent)
    assert agent.tools == [CALCULATOR_SCHEMA, WEB_SEARCH_SCHEMA]
    assert agent.tool_functions == {"calculator": calculator, "web_search": web_search}


def test_every_schema_has_a_registered_function(agent):
    names = {schema["function"]["name"] for schema in agent.tools}
    assert names == set(agent.tool_functions)


@pytest.mark.parametrize("raw", [
    json.dumps(JUDGMENT),
    f"```json\n{json.dumps(JUDGMENT)}\n```",
], ids=["plain", "json-fence"])
def test_judge_relevance_uses_tool_enabled_llm(agent, monkeypatch, raw):
    prompts = []
    monkeypatch.setattr(agent, "_call_llm_with_tools", lambda prompt: prompts.append(prompt) or raw)
    monkeypatch.setattr(agent, "_call_llm",
                        lambda *a, **k: pytest.fail("plain _call_llm should not be used"))

    judgment = agent._judge_relevance({"title": "Scaling laws", "summary": "Compute grows 10x"})

    assert judgment == JUDGMENT
    assert "Title: Scaling laws" in prompts[0]


def test_judge_relevance_falls_back_on_error(agent, monkeypatch):
    monkeypatch.setattr(agent, "_call_llm_with_tools", lambda prompt: "no json here")

    judgment = agent._judge_relevance({"title": "t", "summary": "s"})

    assert judgment["relevant"] is False
    assert judgment["relevance_score"] == 0
    assert judgment["key_topics"] == []
    assert judgment["reasoning"].startswith("Error:")


def test_judge_relevance_runs_real_tool_through_llm_loop(agent, llm_response, llm_tool_call):
    """Model asks for the calculator, gets the real result back, then answers."""
    responses = [
        llm_response(tool_calls=[llm_tool_call("calculator", {"expression": "10 * 3"})]),
        llm_response(json.dumps(JUDGMENT)),
    ]

    with patch("src.agents.base_agent.completion", side_effect=responses) as completion:
        assert agent._judge_relevance({"title": "t", "summary": "s"}) == JUDGMENT

    tool_message = completion.call_args.kwargs["messages"][-1]
    assert tool_message["role"] == "tool"
    assert json.loads(tool_message["content"])["result"] == 30
