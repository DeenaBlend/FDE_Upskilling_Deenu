# tests/test_base_agent.py
"""Unit tests for BaseAgent: model config, LLM retries, tool-call loop, template method.

`completion` is patched in every LLM test, so no real model is called.
"""
import json
from unittest.mock import patch

import pytest
from litellm.exceptions import RateLimitError, ServiceUnavailableError

from src.agents.base_agent import BaseAgent

COMPLETION = "src.agents.base_agent.completion"
SLEEP = "src.agents.base_agent.time.sleep"


class EchoAgent(BaseAgent):
    """Minimal concrete agent that records each template step."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calls = []

    async def _load_context(self, input_path):
        self.calls.append(("load", input_path))
        return {"text": "hello"}

    async def _process(self, context):
        self.calls.append(("process", context))
        return {"text": context["text"].upper()}

    async def _save_result(self, result, output_path):
        self.calls.append(("save", result, output_path))


# litellm's exception constructors want provider details; these subclasses skip
# that but are still caught by `except (ServiceUnavailableError, RateLimitError)`.
class _RateLimited(RateLimitError):
    def __init__(self):
        Exception.__init__(self, "rate limited")

    def __str__(self):
        return "rate limited"


class _Unavailable(ServiceUnavailableError):
    def __init__(self):
        Exception.__init__(self, "unavailable")

    def __str__(self):
        return "unavailable"


# --- Construction -----------------------------------------------------------


def test_requires_a_model(monkeypatch):
    monkeypatch.delenv("LITELLM_MODEL", raising=False)
    with pytest.raises(ValueError, match="No model configured"):
        EchoAgent()


def test_model_from_env(llm_model):
    agent = EchoAgent()

    assert agent.model == llm_model
    assert agent.tools == []
    assert agent.tool_functions == {}


def test_explicit_model_overrides_env(llm_model):
    assert EchoAgent(model="other-model").model == "other-model"


def test_base_agent_is_abstract(llm_model):
    with pytest.raises(TypeError):
        BaseAgent()


def test_register_tool_function(llm_model):
    agent = EchoAgent()
    agent.register_tool_function("double", lambda x: x * 2)
    assert agent.tool_functions["double"](4) == 8


# --- _call_llm --------------------------------------------------------------


def test_call_llm_returns_content_and_sends_system_prompt(llm_model, llm_response):
    with patch(COMPLETION, return_value=llm_response("hi there")) as completion:
        assert EchoAgent()._call_llm("Say hi", system="Be brief") == "hi there"

    completion.assert_called_once_with(
        model=llm_model,
        messages=[
            {"role": "system", "content": "Be brief"},
            {"role": "user", "content": "Say hi"},
        ],
    )


def test_call_llm_without_system_prompt(llm_model, llm_response):
    with patch(COMPLETION, return_value=llm_response("ok")) as completion:
        EchoAgent()._call_llm("ping")

    assert completion.call_args.kwargs["messages"] == [{"role": "user", "content": "ping"}]


@pytest.mark.parametrize("error_cls", [_RateLimited, _Unavailable])
def test_call_llm_retries_transient_errors(llm_model, llm_response, error_cls):
    with patch(COMPLETION, side_effect=[error_cls(), llm_response("recovered")]) as completion, \
         patch(SLEEP) as sleep:
        assert EchoAgent()._call_llm("ping") == "recovered"

    assert completion.call_count == 2
    sleep.assert_called_once_with(5)


def test_call_llm_gives_up_after_three_attempts(llm_model):
    with patch(COMPLETION, side_effect=_RateLimited()) as completion, \
         patch(SLEEP) as sleep:
        with pytest.raises(RateLimitError):
            EchoAgent()._call_llm("ping")

    assert completion.call_count == 3
    assert [c.args[0] for c in sleep.call_args_list] == [5, 10]  # exponential backoff


def test_call_llm_does_not_retry_other_errors(llm_model):
    with patch(COMPLETION, side_effect=ValueError("bad request")) as completion, \
         patch(SLEEP) as sleep:
        with pytest.raises(ValueError, match="bad request"):
            EchoAgent()._call_llm("ping")

    assert completion.call_count == 1
    sleep.assert_not_called()


# --- _call_llm_with_tools ---------------------------------------------------


def test_tool_loop_returns_text_when_no_tool_calls(llm_model, llm_response):
    with patch(COMPLETION, return_value=llm_response("plain answer")) as completion:
        assert EchoAgent()._call_llm_with_tools("question") == "plain answer"

    # No tools configured -> tools=None rather than an empty list
    assert completion.call_args.kwargs["tools"] is None


def test_tool_loop_executes_tool_and_feeds_result_back(llm_model, llm_response, llm_tool_call):
    schema = {"type": "function", "function": {"name": "add"}}
    agent = EchoAgent(tools=[schema])
    agent.register_tool_function("add", lambda a, b: {"sum": a + b})
    responses = [
        llm_response(tool_calls=[llm_tool_call("add", {"a": 2, "b": 3}, call_id="call_1")]),
        llm_response("The sum is 5"),
    ]

    with patch(COMPLETION, side_effect=responses) as completion:
        answer = agent._call_llm_with_tools("What is 2 + 3?", system="Use tools")

    assert answer == "The sum is 5"
    assert completion.call_count == 2
    assert completion.call_args.kwargs["tools"] == [schema]
    messages = completion.call_args.kwargs["messages"]
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "tool"]
    assert messages[-1] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "name": "add",
        "content": json.dumps({"sum": 5}),
    }


def test_tool_loop_handles_empty_arguments(llm_model, llm_response, llm_tool_call):
    agent = EchoAgent()
    agent.register_tool_function("now", lambda: "noon")
    responses = [
        llm_response(tool_calls=[llm_tool_call("now", "")]),
        llm_response("It is noon"),
    ]

    with patch(COMPLETION, side_effect=responses):
        assert agent._call_llm_with_tools("What time is it?") == "It is noon"


def test_tool_loop_unregistered_tool_raises(llm_model, llm_response, llm_tool_call):
    response = llm_response(tool_calls=[llm_tool_call("missing", {})])

    with patch(COMPLETION, return_value=response):
        with pytest.raises(ValueError, match="not registered"):
            EchoAgent()._call_llm_with_tools("q")


def test_tool_loop_stops_after_ten_rounds(llm_model, llm_response, llm_tool_call):
    agent = EchoAgent()
    agent.register_tool_function("noop", lambda: None)
    looping = llm_response(tool_calls=[llm_tool_call("noop", {})])

    with patch(COMPLETION, return_value=looping) as completion:
        with pytest.raises(RuntimeError, match="10 rounds"):
            agent._call_llm_with_tools("q")

    assert completion.call_count == 10


# --- execute (template method) ----------------------------------------------


@pytest.mark.asyncio
async def test_execute_runs_steps_in_order(llm_model):
    agent = EchoAgent()

    result = await agent.execute("in.md", "out.md")

    assert result == {"input_path": "in.md", "output_path": "out.md", "success": True}
    assert agent.calls == [
        ("load", "in.md"),
        ("process", {"text": "hello"}),
        ("save", {"text": "HELLO"}, "out.md"),
    ]
