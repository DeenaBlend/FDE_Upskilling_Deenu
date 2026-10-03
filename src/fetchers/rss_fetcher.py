# src/fetchers/rss_fetcher.py

from src.fetchers.base_fetcher import BaseFetcher
import asyncio
import feedparser
from typing import List
from src.models.article import Article
from src.strategies.rate_limit_strategy import SemaphoreStrategy


class RSSFetcher(BaseFetcher):
    """Fetch from RSS feed."""

    def __init__(self, feed_url: str, transformer, storage, rate_limiter=None):
        super().__init__(transformer, storage)
        self.feed_url = feed_url
        # Use provided strategy or default
        self.rate_limiter = rate_limiter or SemaphoreStrategy(10)

    async def fetch_articles(self) -> List[Article]:
        """Fetch from RSS feed."""
        await self.rate_limiter.acquire()
        try:
            # feedparser is sync, run it in a thread so it doesn't block
            feed = await asyncio.to_thread(feedparser.parse, self.feed_url)
        except Exception as e:
            print(f"⚠️  RSS fetch failed for {self.feed_url}: {e}")
            return []  # Return empty list on error
        finally:
            self.rate_limiter.release()

        return self.transformer.transform_rss(feed.entries)
    
    def get_source_name(self) -> str:
        """Return source name."""
        return "rss"