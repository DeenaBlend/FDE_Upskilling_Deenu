# tests/test_base_fetcher.py
"""Tests for the BaseFetcher template method and the optional fetcher interfaces."""
from datetime import datetime
from unittest.mock import Mock

import pytest

from src.fetchers.base_fetcher import BaseFetcher
from src.fetchers.interfaces import AuthenticatedFetcher, PaginatedFetcher
from src.models.article import Article


class StubFetcher(BaseFetcher):
    def __init__(self, transformer, storage, articles):
        super().__init__(transformer, storage)
        self._articles = articles

    async def fetch_articles(self):
        return self._articles

    def get_source_name(self):
        return "stub"


def _article(title):
    return Article(title=title, url=f"https://example.com/{title}",
                   published_at=datetime(2026, 1, 1), source="stub")


def test_base_fetcher_is_abstract():
    with pytest.raises(TypeError):
        BaseFetcher(Mock(), Mock())


def test_subclass_missing_methods_cannot_be_instantiated():
    class Incomplete(BaseFetcher):
        async def fetch_articles(self):
            return []

    with pytest.raises(TypeError):
        Incomplete(Mock(), Mock())


@pytest.mark.asyncio
async def test_fetch_and_save_uses_source_filename():
    storage = Mock()
    articles = [_article("A"), _article("B")]
    fetcher = StubFetcher(Mock(), storage, articles)

    result = await fetcher.fetch_and_save()

    assert result == articles
    storage.save.assert_called_once_with(articles, "stub_articles.md")


@pytest.mark.asyncio
async def test_fetch_and_save_skips_save_when_empty():
    storage = Mock()
    fetcher = StubFetcher(Mock(), storage, [])

    assert await fetcher.fetch_and_save() == []
    storage.save.assert_not_called()


def test_interfaces_are_abstract():
    with pytest.raises(TypeError):
        AuthenticatedFetcher()
    with pytest.raises(TypeError):
        PaginatedFetcher()


@pytest.mark.asyncio
async def test_fetcher_can_implement_optional_interfaces():
    """ISP: a fetcher opts into only the extra interfaces it needs."""

    class PagedFetcher(StubFetcher, PaginatedFetcher, AuthenticatedFetcher):
        async def authenticate(self):
            return True

        async def fetch_page(self, page):
            return self._articles[page - 1:page]

    articles = [_article("A"), _article("B")]
    fetcher = PagedFetcher(Mock(), Mock(), articles)

    assert isinstance(fetcher, BaseFetcher)
    assert await fetcher.authenticate() is True
    assert await fetcher.fetch_page(2) == [articles[1]]
