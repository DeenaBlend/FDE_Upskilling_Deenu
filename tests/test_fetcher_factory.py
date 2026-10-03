# tests/test_fetcher_factory.py
"""Unit tests for FetcherFactory (no network)."""
from unittest.mock import Mock

import pytest

from src.factories.fetcher_factory import FetcherFactory
from src.fetchers.base_fetcher import BaseFetcher
from src.fetchers.github_trending_fetcher import GitHubTrendingFetcher
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.fetchers.rss_fetcher import RSSFetcher


@pytest.fixture
def deps():
    return Mock(name="transformer"), Mock(name="storage")


@pytest.mark.parametrize("source_type, expected_class", [
    ("hackernews", HackerNewsFetcher),
    ("github", GitHubTrendingFetcher),
])
def test_create_standard_fetchers(deps, source_type, expected_class):
    transformer, storage = deps

    fetcher = FetcherFactory.create(source_type, transformer, storage)

    assert isinstance(fetcher, expected_class)
    assert fetcher.transformer is transformer
    assert fetcher.storage is storage


def test_create_rss_with_feed_url(deps):
    fetcher = FetcherFactory.create("rss", *deps, feed_url="https://example.com/feed")

    assert isinstance(fetcher, RSSFetcher)
    assert fetcher.feed_url == "https://example.com/feed"


def test_create_rss_without_feed_url_raises(deps):
    with pytest.raises(ValueError, match="feed_url"):
        FetcherFactory.create("rss", *deps)


def test_create_unknown_type_raises(deps):
    with pytest.raises(ValueError, match="Unknown fetcher type"):
        FetcherFactory.create("twitter", *deps)


def test_create_passes_extra_kwargs(deps):
    limiter = Mock()

    hn = FetcherFactory.create("hackernews", *deps, rate_limiter=limiter)
    rss = FetcherFactory.create(
        "rss", *deps, feed_url="https://example.com/feed", rate_limiter=limiter
    )

    assert hn.rate_limiter is limiter
    assert rss.rate_limiter is limiter


def test_register_new_fetcher(deps, monkeypatch):
    """New sources can be added without modifying the factory (OCP)."""

    class DummyFetcher(BaseFetcher):
        async def fetch_articles(self):
            return []

        def get_source_name(self):
            return "dummy"

    # Work on a copy so the registration doesn't leak into other tests
    monkeypatch.setattr(FetcherFactory, "_fetchers", dict(FetcherFactory._fetchers))

    FetcherFactory.register("dummy", DummyFetcher)

    assert "dummy" in FetcherFactory.get_available_types()
    assert isinstance(FetcherFactory.create("dummy", *deps), DummyFetcher)


def test_available_types():
    assert set(FetcherFactory.get_available_types()) >= {"hackernews", "github", "rss"}
