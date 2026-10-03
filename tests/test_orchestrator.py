# tests/test_orchestrator.py

import pytest
from unittest.mock import Mock, AsyncMock
from src.orchestrator import FetchOrchestrator
from src.models.article import Article
from datetime import datetime


@pytest.mark.asyncio
async def test_orchestrator_with_mocks():
    """
    Test orchestrator with mocked dependencies.
    
    DIP makes this easy - just inject mocks!
    """
    # Create mock fetcher
    mock_fetcher = Mock()
    mock_fetcher.fetch_and_save = AsyncMock(return_value=[
        Article(
            title="Test",
            url="http://test.com",
            published_at=datetime.now(),
            source="test",
            summary="Test"
        )
    ])
    
    # Create mock storage
    mock_storage = Mock()
    
    # Inject mocks into orchestrator
    orchestrator = FetchOrchestrator(
        fetchers=[mock_fetcher],
        storage=mock_storage
    )
    
    # Test
    articles = await orchestrator.fetch_all()
    
    # Verify
    assert len(articles) == 1
    assert articles[0].title == "Test"
    assert mock_fetcher.fetch_and_save.called
    assert mock_storage.save.called


@pytest.mark.asyncio
async def test_multiple_fetchers():
    """Test with multiple mock fetchers."""
    mock_fetcher1 = Mock()
    mock_fetcher1.fetch_and_save = AsyncMock(return_value=[
        Article(title="Article 1", url="http://1.com", 
                published_at=datetime.now(), source="test", summary="Test")
    ])
    
    mock_fetcher2 = Mock()
    mock_fetcher2.fetch_and_save = AsyncMock(return_value=[
        Article(title="Article 2", url="http://2.com",
                published_at=datetime.now(), source="test", summary="Test")
    ])
    
    orchestrator = FetchOrchestrator(
        fetchers=[mock_fetcher1, mock_fetcher2],
        storage=Mock()
    )
    
    articles = await orchestrator.fetch_all()

    assert len(articles) == 2
    print("✅ Multiple fetchers work!")


def _mock_fetcher(name, result=None, error=None):
    fetcher = Mock()
    fetcher.get_source_name.return_value = name
    fetcher.fetch_and_save = AsyncMock(return_value=result or [], side_effect=error)
    return fetcher


def _article(title):
    return Article(title=title, url=f"https://example.com/{title}",
                   published_at=datetime(2026, 1, 1), source="test")


@pytest.mark.asyncio
async def test_failing_fetcher_does_not_break_others():
    """One fetcher raising must not lose the other fetchers' articles."""
    good = _mock_fetcher("good", [_article("A")])
    bad = _mock_fetcher("bad", error=RuntimeError("boom"))
    storage = Mock()

    articles = await FetchOrchestrator([bad, good], storage).fetch_all()

    assert [a.title for a in articles] == ["A"]
    bad.get_source_name.assert_called()  # used in the warning message
    storage.save.assert_called_once_with(articles, "all_articles.md")


@pytest.mark.asyncio
async def test_no_combined_save_when_nothing_fetched():
    storage = Mock()
    fetchers = [_mock_fetcher("empty"), _mock_fetcher("bad", error=RuntimeError())]

    articles = await FetchOrchestrator(fetchers, storage).fetch_all()

    assert articles == []
    storage.save.assert_not_called()


@pytest.mark.asyncio
async def test_results_keep_fetcher_order():
    first = _mock_fetcher("first", [_article("1a"), _article("1b")])
    second = _mock_fetcher("second", [_article("2a")])

    articles = await FetchOrchestrator([first, second], Mock()).fetch_all()

    assert [a.title for a in articles] == ["1a", "1b", "2a"]


@pytest.mark.asyncio
async def test_no_fetchers():
    storage = Mock()
    assert await FetchOrchestrator([], storage).fetch_all() == []
    storage.save.assert_not_called()