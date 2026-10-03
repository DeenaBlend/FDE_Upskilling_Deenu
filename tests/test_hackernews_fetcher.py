# tests/test_hackernews_fetcher.py

import pytest
from src.fetchers.hackernews_fetcher import HackerNewsFetcher
from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage


@pytest.mark.asyncio
async def test_hackernews_fetcher():
    """Test HackerNews fetcher with new architecture."""
    transformer = ArticleTransformer()
    storage = MarkdownStorage("data/test_articles")
    
    fetcher = HackerNewsFetcher(
        transformer=transformer,
        storage=storage
    )
    
    articles = await fetcher.fetch_articles()
    
    assert len(articles) > 0
    assert all(hasattr(a, 'title') for a in articles)