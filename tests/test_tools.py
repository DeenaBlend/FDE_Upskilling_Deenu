# tests/test_tools.py
"""Unit tests for the agent tools (calculator, web_search) and their LLM schemas."""
import inspect

import pytest

from src.tools.calculator import CALCULATOR_SCHEMA, calculator
from src.tools.web_search import WEB_SEARCH_SCHEMA, web_search


@pytest.mark.parametrize("expression, expected", [
    ("2 + 2", 4),
    ("10 * 5 + 3", 53),
    ("(1 + 2) * 3", 9),
    ("7 / 2", 3.5),
    ("2 ** 10", 1024),
    ("-4 + 1", -3),
])
def test_calculator_evaluates(expression, expected):
    assert calculator(expression) == {
        "success": True,
        "result": expected,
        "expression": expression,
    }


@pytest.mark.parametrize("expression", ["1 / 0", "2 +", "hello", ""])
def test_calculator_reports_errors(expression):
    result = calculator(expression)

    assert result["success"] is False
    assert result["error"]
    assert result["expression"] == expression


@pytest.mark.parametrize("expression", [
    "__import__('os').getcwd()",
    "open('/etc/passwd').read()",
    "len('abc')",
])
def test_calculator_blocks_builtins(expression):
    result = calculator(expression)

    assert result["success"] is False
    assert "not defined" in result["error"]


def test_web_search_defaults():
    result = web_search("AI news")

    assert result["success"] is True
    assert result["query"] == "AI news"
    assert result["num_results"] == 3
    assert len(result["results"]) == 3
    assert all("AI news" in r["title"] for r in result["results"])


@pytest.mark.parametrize("n", [0, 1, 5])
def test_web_search_respects_num_results(n):
    assert len(web_search("llm", num_results=n)["results"]) == n


def test_web_search_result_shape():
    [item] = web_search("transformers", num_results=1)["results"]

    assert set(item) == {"title", "url", "snippet"}
    assert item["url"].startswith("https://")


@pytest.mark.parametrize("schema, func", [
    (CALCULATOR_SCHEMA, calculator),
    (WEB_SEARCH_SCHEMA, web_search),
])
def test_schema_matches_function_signature(schema, func):
    """The schema sent to the LLM must line up with the Python function it calls."""
    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == func.__name__

    params = inspect.signature(func).parameters
    assert set(fn["parameters"]["properties"]) == set(params)

    required = {n for n, p in params.items() if p.default is inspect.Parameter.empty}
    assert set(fn["parameters"]["required"]) == required
