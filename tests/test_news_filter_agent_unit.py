# tests/test_news_filter_agent_unit.py
"""Offline unit tests for NewsFilterAgent.

The LLM call is stubbed, so results are deterministic
(test_news_filter_agent.py exercises the real model).
"""
import json
from datetime import datetime

import pytest

from src.agents.news_filter_agent import NewsFilterAgent
from src.models.article import Article
from src.storage.markdown_storage import MarkdownStorage

VALID_JUDGMENT = {
    "relevant": True,
    "relevance_score": 9,
    "reasoning": "LLM release",
    "key_topics": ["LLM"],
}
VALID_JSON = json.dumps(VALID_JUDGMENT)


@pytest.fixture
def agent(llm_model):
    return NewsFilterAgent()


def _judgment(relevant=True, score=8, reasoning="AI news", topics=("LLM",)):
    return {
        "relevant": relevant,
        "relevance_score": score,
        "reasoning": reasoning,
        "key_topics": list(topics),
    }


# --- _parse_markdown --------------------------------------------------------


def test_parse_markdown_extracts_articles(agent):
    content = """# News Articles

**Total Articles:** 2

---

## GPT-5 announced

**Source:** hackernews
**URL:** https://example.com/gpt5
**Score:** 10

OpenAI announces GPT-5.

---

## Rust 2.0

**URL:** https://example.com/rust

A systems language update.
"""
    assert agent._parse_markdown(content) == [
        {"title": "GPT-5 announced", "url": "https://example.com/gpt5",
         "summary": "OpenAI announces GPT-5."},
        {"title": "Rust 2.0", "url": "https://example.com/rust",
         "summary": "A systems language update."},
    ]


def test_parse_markdown_reads_markdown_storage_output(agent, tmp_path):
    """The agent must understand exactly what the fetch stage writes."""
    articles = [
        Article("LLM breakthrough", "https://example.com/llm", datetime(2026, 1, 1),
                "hackernews", summary="New model beats benchmarks"),
        Article("Database tips", "https://example.com/db", datetime(2026, 1, 2),
                "rss", summary="Index your tables"),
    ]
    path = MarkdownStorage(str(tmp_path)).save(articles, "all_articles.md")

    parsed = agent._parse_markdown(path.read_text())

    assert [(a["title"], a["url"], a["summary"]) for a in parsed] == [
        ("LLM breakthrough", "https://example.com/llm", "New model beats benchmarks"),
        ("Database tips", "https://example.com/db", "Index your tables"),
    ]


def test_parse_markdown_missing_url_and_non_article_sections(agent):
    content = "Intro text\n---\n## Only a title\n\nJust a summary\n---\nTrailing notes"

    assert agent._parse_markdown(content) == [
        {"title": "Only a title", "url": "", "summary": "Just a summary"}
    ]


@pytest.mark.xfail(
    strict=True,
    reason="Bug: when an article has no summary, the '## title' line is used as the summary",
)
def test_parse_markdown_article_without_summary(agent):
    md = Article("Title only", "https://example.com/t", datetime(2026, 1, 1),
                 "hackernews").to_markdown()

    [article] = agent._parse_markdown(md)

    assert article["summary"] == ""


# --- _judge_relevance -------------------------------------------------------


@pytest.mark.parametrize("raw", [
    VALID_JSON,
    f"```json\n{VALID_JSON}\n```",
    f"Here you go:\n```\n{VALID_JSON}\n```",
], ids=["plain", "json-fence", "bare-fence"])
def test_judge_relevance_parses_json_variants(agent, monkeypatch, raw):
    monkeypatch.setattr(agent, "_call_llm", lambda prompt: raw)

    assert agent._judge_relevance({"title": "GPT-5", "summary": "New model"}) == VALID_JUDGMENT


def test_judge_relevance_prompt_includes_article(agent, monkeypatch):
    prompts = []
    monkeypatch.setattr(agent, "_call_llm", lambda prompt: prompts.append(prompt) or VALID_JSON)

    agent._judge_relevance({"title": "Diffusion models", "summary": "Image generation"})

    assert "Title: Diffusion models" in prompts[0]
    assert "Summary: Image generation" in prompts[0]


@pytest.mark.parametrize("raw", ["not json", '{"relevant": true}', ""],
                         ids=["garbage", "missing-keys", "empty"])
def test_judge_relevance_falls_back_on_bad_output(agent, monkeypatch, raw):
    monkeypatch.setattr(agent, "_call_llm", lambda prompt: raw)

    judgment = agent._judge_relevance({"title": "t", "summary": "s"})

    assert judgment["relevant"] is False
    assert judgment["relevance_score"] == 0
    assert judgment["key_topics"] == []
    assert judgment["reasoning"].startswith("Failed to judge")


def test_judge_relevance_falls_back_when_llm_errors(agent, monkeypatch):
    def boom(prompt):
        raise RuntimeError("LLM down")

    monkeypatch.setattr(agent, "_call_llm", boom)

    judgment = agent._judge_relevance({"title": "t", "summary": "s"})

    assert judgment["relevant"] is False
    assert "LLM down" in judgment["reasoning"]


# --- _process ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_applies_relevance_threshold(agent, monkeypatch):
    judgments = {
        "below threshold": _judgment(score=5),
        "at threshold": _judgment(score=6),
        "not relevant": _judgment(relevant=False, score=9),
        "no topics": {"relevant": True, "relevance_score": 10, "reasoning": "big"},
    }
    monkeypatch.setattr(agent, "_judge_relevance", lambda article: judgments[article["title"]])
    articles = [{"title": t, "url": f"https://example.com/{i}", "summary": "s"}
                for i, t in enumerate(judgments)]

    result = await agent._process({"articles": articles})

    assert [a["title"] for a in result["filtered_articles"]] == ["at threshold", "no topics"]
    assert (result["total_input"], result["total_output"]) == (4, 2)
    kept, no_topics = result["filtered_articles"]
    assert kept["relevance_score"] == 6
    assert kept["reasoning"] == "AI news"
    assert kept["key_topics"] == ["LLM"]
    assert kept["url"] == "https://example.com/1"
    assert no_topics["key_topics"] == []


# --- _save_result -----------------------------------------------------------


@pytest.mark.asyncio
async def test_save_result_writes_markdown(agent, tmp_path):
    output = tmp_path / "nested" / "filtered.md"
    result = {
        "filtered_articles": [{
            "title": "GPT-5", "url": "https://example.com/gpt5", "summary": "New model",
            "relevance_score": 9, "reasoning": "LLM release", "key_topics": ["LLM", "OpenAI"],
        }],
        "total_input": 4,
        "total_output": 1,
    }

    await agent._save_result(result, str(output))

    content = output.read_text()
    assert "**Total Input:** 4" in content
    assert "**Total Output:** 1" in content
    assert "**Filter Rate:** 25.0%" in content
    assert "## GPT-5" in content
    assert "**URL:** https://example.com/gpt5" in content
    assert "**Relevance Score:** 9/10" in content
    assert "**Key Topics:** LLM, OpenAI" in content


@pytest.mark.xfail(
    strict=True,
    raises=ZeroDivisionError,
    reason="Bug: Filter Rate divides by total_input, which is 0 for an empty input file",
)
@pytest.mark.asyncio
async def test_save_result_with_no_input_articles(agent, tmp_path):
    result = {"filtered_articles": [], "total_input": 0, "total_output": 0}
    await agent._save_result(result, str(tmp_path / "filtered.md"))


# --- execute ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_end_to_end_with_stubbed_llm(agent, monkeypatch, tmp_path):
    input_file = tmp_path / "input.md"
    input_file.write_text("""
## GPT-4 Released by OpenAI

**URL:** https://example.com/gpt4

OpenAI announces GPT-4 with enhanced capabilities.

---

## New JavaScript Framework

**URL:** https://example.com/js

React alternative for web development.
""")

    def fake_llm(prompt):
        # The prompt template has examples mentioning both titles, so match on "Title: ..."
        if "Title: GPT-4" in prompt:
            return json.dumps(_judgment(score=10))
        return json.dumps(_judgment(relevant=False, score=1, topics=()))

    monkeypatch.setattr(agent, "_call_llm", fake_llm)
    output_file = tmp_path / "out" / "filtered.md"

    result = await agent.execute(str(input_file), str(output_file))

    assert result["success"] is True
    content = output_file.read_text()
    assert "GPT-4 Released by OpenAI" in content
    assert "New JavaScript Framework" not in content
    assert "**Total Output:** 1" in content
