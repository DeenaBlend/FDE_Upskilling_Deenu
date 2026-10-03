# tests/test_summarizer_agent.py
"""Offline tests for SummarizerAgent (LLM calls are stubbed)."""
import pytest

from src.agents.news_filter_agent import NewsFilterAgent
from src.agents.summarizer_agent import SummarizerAgent
from src.skills.search_skill import SearchSkill

FILTERED_MD = """# Filtered AI/ML Articles

**Total Input:** 5
**Total Output:** 3

---

## GPT-5 released

**URL:** https://example.com/gpt5
**Relevance Score:** 10/10
**Reasoning:** Major LLM release
**Key Topics:** LLM, OpenAI

New model.

---

## Claude update

**URL:** https://example.com/claude
**Relevance Score:** 9/10
**Reasoning:** Another LLM
**Key Topics:** LLM

Update.

---

## Robot arm demo

**URL:** https://example.com/robot
**Relevance Score:** 7/10
**Reasoning:** Robotics with ML

Demo.

---
"""


@pytest.fixture
def agent(llm_model):
    return SummarizerAgent()


def test_init_creates_search_skill(agent):
    assert isinstance(agent.search_skill, SearchSkill)


def test_parse_markdown_extracts_fields(agent):
    assert agent._parse_markdown(FILTERED_MD) == [
        {"title": "GPT-5 released", "relevance": 10,
         "reasoning": "Major LLM release", "topics": "LLM, OpenAI"},
        {"title": "Claude update", "relevance": 9,
         "reasoning": "Another LLM", "topics": "LLM"},
        {"title": "Robot arm demo", "relevance": 7,
         "reasoning": "Robotics with ML", "topics": ""},
    ]


def test_parse_markdown_defaults_for_missing_fields(agent):
    assert agent._parse_markdown("## Bare title\n\nNo metadata") == [
        {"title": "Bare title", "relevance": 0, "reasoning": "", "topics": ""}
    ]


@pytest.mark.asyncio
async def test_reads_news_filter_agent_output(agent, tmp_path):
    """Contract test: the summarizer parses exactly what the filter agent writes."""
    filtered_path = tmp_path / "filtered.md"
    await NewsFilterAgent()._save_result({
        "filtered_articles": [
            {"title": "GPT-5 released", "url": "https://example.com/gpt5", "summary": "New model",
             "relevance_score": 9, "reasoning": "Major LLM release",
             "key_topics": ["LLM", "OpenAI"]},
            {"title": "Untagged", "url": "https://example.com/u", "summary": "Misc",
             "relevance_score": 6, "reasoning": "Borderline", "key_topics": []},
        ],
        "total_input": 4,
        "total_output": 2,
    }, str(filtered_path))

    context = await agent._load_context(str(filtered_path))

    assert context["articles"] == [
        {"title": "GPT-5 released", "relevance": 9,
         "reasoning": "Major LLM release", "topics": "LLM, OpenAI"},
        {"title": "Untagged", "relevance": 6, "reasoning": "Borderline", "topics": ""},
    ]


@pytest.mark.asyncio
async def test_process_groups_by_first_topic(agent, monkeypatch):
    prompts = []

    def fake_llm(prompt):
        prompts.append(prompt)
        return "  A summary.  "

    monkeypatch.setattr(agent, "_call_llm", fake_llm)

    result = await agent._process({"articles": agent._parse_markdown(FILTERED_MD)})

    assert list(result["topics"]) == ["LLM", "Other"]
    assert [a["title"] for a in result["topics"]["LLM"]] == ["GPT-5 released", "Claude update"]
    assert [a["title"] for a in result["topics"]["Other"]] == ["Robot arm demo"]
    assert result["summaries"] == {"LLM": "A summary.", "Other": "A summary."}
    assert result["total_articles"] == 3
    assert len(prompts) == 2  # one LLM call per topic


@pytest.mark.asyncio
async def test_summarize_topic_prompt_lists_articles(agent, monkeypatch):
    prompts = []
    monkeypatch.setattr(agent, "_call_llm", lambda prompt: prompts.append(prompt) or "ok")

    await agent._summarize_topic("LLM", [
        {"title": "GPT-5", "reasoning": "Big release"},
        {"title": "Claude", "reasoning": "Update"},
    ])

    assert "LLM articles" in prompts[0]
    assert "- GPT-5: Big release" in prompts[0]
    assert "- Claude: Update" in prompts[0]


@pytest.mark.asyncio
async def test_save_result_writes_digest(agent, tmp_path):
    output = tmp_path / "context" / "summary.md"

    await agent._save_result({
        "topics": {"LLM": [{}, {}], "Other": [{}]},
        "summaries": {"LLM": "LLMs everywhere.", "Other": "Misc."},
        "total_articles": 3,
    }, str(output))

    content = output.read_text()
    assert content.startswith("# AI/ML Daily Digest - Summary")
    assert "**Total Articles:** 3" in content
    assert "## LLM (2 articles)\n\nLLMs everywhere." in content
    assert "## Other (1 articles)\n\nMisc." in content


@pytest.mark.asyncio
async def test_execute_with_no_articles_skips_llm(agent, monkeypatch, tmp_path):
    monkeypatch.setattr(agent, "_call_llm",
                        lambda prompt: pytest.fail("LLM should not be called"))
    source = tmp_path / "filtered.md"
    source.write_text("# Filtered AI/ML Articles\n\n---\n")
    output = tmp_path / "summary.md"

    await agent.execute(str(source), str(output))

    assert "**Total Articles:** 0" in output.read_text()
