# tests/test_pipelines.py
"""Wiring tests for the entry-point scripts (main, pipeline, complete_pipeline).

Every collaborator (fetchers, storage, agents, database) is replaced with a mock,
so nothing touches the network, the LLM, or the real data/ directory.
"""
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src import complete_pipeline, pipeline
from src import main as main_module
from src.models.article import Article

ARTICLES = [
    Article("LLM news", "https://example.com/llm", datetime(2026, 1, 1, 9, 30),
            "hackernews", summary="s", score=7),
]
FETCH_OUTPUT = str(Path("data/articles/all_articles.md"))
FILTER_OUTPUT = str(Path("data/context/filtered_articles.md"))
SUMMARY_OUTPUT = str(Path("data/context/summary.md"))
NEWSLETTER_OUTPUT = str(Path("data/output/newsletter.md"))


@pytest.fixture(autouse=True)
def isolate_cwd(tmp_path, monkeypatch):
    """Safety net: any stray relative-path write lands in tmp_path, not the repo."""
    monkeypatch.chdir(tmp_path)


def _patch_fetch_stage(monkeypatch, module):
    factory = MagicMock()
    factory.create.side_effect = lambda source_type, *args, **kwargs: f"{source_type}-fetcher"
    orchestrator_cls = MagicMock()
    orchestrator_cls.return_value.fetch_all = AsyncMock(return_value=ARTICLES)
    storage_cls = MagicMock()

    monkeypatch.setattr(module, "FetcherFactory", factory)
    monkeypatch.setattr(module, "FetchOrchestrator", orchestrator_cls)
    monkeypatch.setattr(module, "MarkdownStorage", storage_cls)
    monkeypatch.setattr(module, "ArticleTransformer", MagicMock())
    return factory, orchestrator_cls, storage_cls


def _assert_standard_fetch_stage(factory, orchestrator_cls, storage_cls):
    storage_cls.assert_called_once_with("data/articles")
    calls = factory.create.call_args_list
    assert [c.args[0] for c in calls] == ["hackernews", "rss", "github"]
    assert calls[1].kwargs == {"feed_url": "https://hnrss.org/frontpage"}
    orchestrator_cls.assert_called_once_with(
        fetchers=["hackernews-fetcher", "rss-fetcher", "github-fetcher"],
        storage=storage_cls.return_value,
    )
    orchestrator_cls.return_value.fetch_all.assert_awaited_once()


def _recording_agent(name, order):
    """Mock agent class whose execute() records (name, input_path, output_path)."""
    agent_cls = MagicMock()

    async def execute(input_path, output_path):
        order.append((name, input_path, output_path))
        return {"success": True}

    agent_cls.return_value.execute = execute
    return agent_cls


@pytest.mark.asyncio
async def test_main_wires_fetchers_into_orchestrator(monkeypatch):
    stage = _patch_fetch_stage(monkeypatch, main_module)

    await main_module.main()

    _assert_standard_fetch_stage(*stage)


@pytest.mark.asyncio
async def test_pipeline_fetches_then_filters(monkeypatch):
    stage = _patch_fetch_stage(monkeypatch, pipeline)
    order = []
    monkeypatch.setattr(pipeline, "NewsFilterAgent", _recording_agent("filter", order))

    await pipeline.run_pipeline()

    _assert_standard_fetch_stage(*stage)
    assert order == [("filter", FETCH_OUTPUT, FILTER_OUTPUT)]


@pytest.mark.asyncio
async def test_complete_pipeline_runs_all_stages_in_order(monkeypatch):
    stage = _patch_fetch_stage(monkeypatch, complete_pipeline)

    db = MagicMock()
    db.initialize = AsyncMock()
    db.insert_article = AsyncMock()
    db.query_articles = AsyncMock(return_value=[{"id": 1}])
    monkeypatch.setattr(complete_pipeline, "DatabaseManager", MagicMock(return_value=db))

    order = []
    monkeypatch.setattr(complete_pipeline, "NewsFilterAgent", _recording_agent("filter", order))
    monkeypatch.setattr(complete_pipeline, "SummarizerAgent", _recording_agent("summarize", order))
    monkeypatch.setattr(complete_pipeline, "WriterAgent", _recording_agent("write", order))

    await complete_pipeline.run_complete_pipeline()

    _assert_standard_fetch_stage(*stage)
    db.initialize.assert_awaited_once()
    db.insert_article.assert_awaited_once_with({
        "title": "LLM news",
        "url": "https://example.com/llm",
        "source": "hackernews",
        "published_at": "2026-01-01T09:30:00",
        "summary": "s",
        "score": 7,
    })
    # Each agent reads the previous agent's output
    assert order == [
        ("filter", FETCH_OUTPUT, FILTER_OUTPUT),
        ("summarize", FILTER_OUTPUT, SUMMARY_OUTPUT),
        ("write", SUMMARY_OUTPUT, NEWSLETTER_OUTPUT),
    ]
