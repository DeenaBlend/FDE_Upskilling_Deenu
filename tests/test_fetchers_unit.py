# tests/test_fetchers_unit.py
"""Offline unit tests for the concrete fetchers.

aiohttp / feedparser are mocked, so these run without network access
(test_fetchers_integration.py covers the real endpoints).
"""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest

from src.fetchers.github_trending_fetcher import GitHubTrendingFetcher
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.fetchers.rss_fetcher import RSSFetcher
from src.strategies.rate_limit_strategy import SemaphoreStrategy
from src.transformers.article_transformer import ArticleTransformer

TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_SESSION = "src.fetchers.hackernews_fetcher.aiohttp.ClientSession"
GITHUB_SESSION = "src.fetchers.github_trending_fetcher.aiohttp.ClientSession"
FEEDPARSER_PARSE = "src.fetchers.rss_fetcher.feedparser.parse"


@pytest.fixture
def rate_limiter():
    limiter = Mock()
    limiter.acquire = AsyncMock()
    return limiter


@pytest.mark.parametrize("make_fetcher, source", [
    (lambda: HackerNewsFetcher(Mock(), Mock()), "hackernews"),
    (lambda: RSSFetcher("https://example.com/feed", Mock(), Mock()), "rss"),
    (lambda: GitHubTrendingFetcher(Mock(), Mock()), "github_trending"),
])
def test_default_rate_limiter_and_source_name(make_fetcher, source):
    fetcher = make_fetcher()
    assert isinstance(fetcher.rate_limiter, SemaphoreStrategy)
    assert fetcher.get_source_name() == source


# --- HackerNews -------------------------------------------------------------


def _hn_item(story_id):
    return {
        "id": story_id,
        "title": f"Story {story_id}",
        "url": f"https://example.com/{story_id}",
        "time": 1_700_000_000,
        "score": story_id,
    }


@pytest.mark.asyncio
async def test_hackernews_fetches_top_30_stories(monkeypatch):
    fetcher = HackerNewsFetcher(ArticleTransformer(), Mock())
    requested = []

    async def fake_get_json(session, url):
        requested.append(url)
        if url == TOP_STORIES_URL:
            return list(range(1, 51))
        story_id = int(url.rsplit("/", 1)[-1].removesuffix(".json"))
        return _hn_item(story_id)

    monkeypatch.setattr(fetcher, "_get_json", fake_get_json)
    with patch(HN_SESSION):
        articles = await fetcher.fetch_articles()

    assert len(articles) == 30
    assert len(requested) == 31  # 1 top-stories call + 30 item calls
    assert articles[0].title == "Story 1"
    assert articles[0].source == "hackernews"


@pytest.mark.asyncio
async def test_hackernews_skips_failed_and_deleted_items(monkeypatch):
    fetcher = HackerNewsFetcher(ArticleTransformer(), Mock())

    async def fake_get_json(session, url):
        if url == TOP_STORIES_URL:
            return [1, 2, 3]
        if url.endswith("/1.json"):
            raise aiohttp.ClientError("timeout")
        if url.endswith("/2.json"):
            return None  # deleted item
        return _hn_item(3)

    monkeypatch.setattr(fetcher, "_get_json", fake_get_json)
    with patch(HN_SESSION):
        articles = await fetcher.fetch_articles()

    assert [a.title for a in articles] == ["Story 3"]


@pytest.mark.asyncio
async def test_hackernews_returns_empty_list_on_failure(monkeypatch):
    fetcher = HackerNewsFetcher(ArticleTransformer(), Mock())
    monkeypatch.setattr(
        fetcher, "_get_json", AsyncMock(side_effect=aiohttp.ClientError("down"))
    )

    with patch(HN_SESSION):
        assert await fetcher.fetch_articles() == []


def _mock_session(json_result=None, error=None):
    session = MagicMock()
    if error is not None:
        session.get.side_effect = error
    else:
        response = session.get.return_value.__aenter__.return_value
        response.json = AsyncMock(return_value=json_result)
    return session


@pytest.mark.asyncio
async def test_hackernews_get_json_is_rate_limited(rate_limiter):
    fetcher = HackerNewsFetcher(Mock(), Mock(), rate_limiter=rate_limiter)
    session = _mock_session(json_result={"id": 1})

    assert await fetcher._get_json(session, "https://example.com/1.json") == {"id": 1}

    session.get.assert_called_once_with("https://example.com/1.json")
    rate_limiter.acquire.assert_awaited_once()
    rate_limiter.release.assert_called_once()


@pytest.mark.asyncio
async def test_hackernews_get_json_releases_limiter_on_error(rate_limiter):
    fetcher = HackerNewsFetcher(Mock(), Mock(), rate_limiter=rate_limiter)
    session = _mock_session(error=aiohttp.ClientError("boom"))

    with pytest.raises(aiohttp.ClientError):
        await fetcher._get_json(session, "https://example.com/1.json")

    rate_limiter.release.assert_called_once()


# --- RSS --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rss_parses_feed_and_transforms_entries(rate_limiter):
    transformer = Mock()
    transformer.transform_rss.return_value = ["article"]
    fetcher = RSSFetcher("https://example.com/feed", transformer, Mock(),
                         rate_limiter=rate_limiter)
    entries = [{"title": "t", "link": "https://example.com/t"}]

    with patch(FEEDPARSER_PARSE, return_value=SimpleNamespace(entries=entries)) as parse:
        result = await fetcher.fetch_articles()

    assert result == ["article"]
    parse.assert_called_once_with("https://example.com/feed")
    transformer.transform_rss.assert_called_once_with(entries)
    rate_limiter.acquire.assert_awaited_once()
    rate_limiter.release.assert_called_once()


@pytest.mark.asyncio
async def test_rss_with_real_transformer(rate_limiter):
    fetcher = RSSFetcher("https://example.com/feed", ArticleTransformer(), Mock(),
                         rate_limiter=rate_limiter)
    entries = [
        {"title": "Kept", "link": "https://example.com/kept", "summary": "<p>Hi</p>"},
        {"title": "No link"},
    ]

    with patch(FEEDPARSER_PARSE, return_value=SimpleNamespace(entries=entries)):
        articles = await fetcher.fetch_articles()

    assert [(a.title, a.source, a.summary) for a in articles] == [("Kept", "rss", "Hi")]


@pytest.mark.asyncio
async def test_rss_returns_empty_list_on_failure(rate_limiter):
    transformer = Mock()
    fetcher = RSSFetcher("https://example.com/feed", transformer, Mock(),
                         rate_limiter=rate_limiter)

    with patch(FEEDPARSER_PARSE, side_effect=OSError("unreachable")):
        assert await fetcher.fetch_articles() == []

    transformer.transform_rss.assert_not_called()
    rate_limiter.release.assert_called_once()


# --- GitHub Trending --------------------------------------------------------


@contextmanager
def github_returns(html=None, error=None):
    """Patch aiohttp so the GitHub fetcher receives `html`, or raises `error`."""
    with patch(GITHUB_SESSION) as session_cls:
        if error is not None:
            session_cls.side_effect = error
        else:
            session = session_cls.return_value.__aenter__.return_value
            response = session.get.return_value.__aenter__.return_value
            response.text = AsyncMock(return_value=html)
        yield session_cls


@pytest.mark.asyncio
async def test_github_page_without_repos(rate_limiter):
    fetcher = GitHubTrendingFetcher(Mock(), Mock(), rate_limiter=rate_limiter)

    with github_returns("<html><body>Nothing trending</body></html>"):
        assert await fetcher.fetch_articles() == []


@pytest.mark.asyncio
async def test_github_returns_empty_list_on_failure(rate_limiter):
    fetcher = GitHubTrendingFetcher(Mock(), Mock(), rate_limiter=rate_limiter)

    with github_returns(error=aiohttp.ClientError("blocked")):
        assert await fetcher.fetch_articles() == []

    rate_limiter.release.assert_called_once()
