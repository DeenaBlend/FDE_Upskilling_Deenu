# src/fetchers/hackernews_fetcher.py

from src.fetchers.base_fetcher import BaseFetcher
from typing import List
import asyncio
import aiohttp
from src.models.article import Article
from src.strategies.rate_limit_strategy import SemaphoreStrategy


class HackerNewsFetcher(BaseFetcher):
    """
    Fetch top stories from HackerNews.
    
    Inherits from BaseFetcher.
    Only implements source-specific logic.
    """

    def __init__(self, transformer, storage, rate_limiter=None):
        super().__init__(transformer, storage)
        # Use provided strategy or default
        self.rate_limiter = rate_limiter or SemaphoreStrategy(10)
    
    async def fetch_articles(self) -> List[Article]:
        """Fetch from HackerNews API."""
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"

        try:
            async with aiohttp.ClientSession() as session:
                # Get top story IDs
                story_ids = await self._get_json(session, url)

                # Fetch first 30 stories concurrently
                tasks = [
                    self._get_json(
                        session,
                        f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    )
                    for story_id in story_ids[:30]
                ]
                items = await asyncio.gather(*tasks, return_exceptions=True)

                # Skip failed requests and deleted items (API returns null)
                stories = [item for item in items if isinstance(item, dict)]

                # Transform using injected transformer
                return self.transformer.transform_hackernews(stories)
        except Exception as e:
            print(f"⚠️  HackerNews fetch failed: {e}")
            return []  # Return empty list on error

    async def _get_json(self, session: aiohttp.ClientSession, url: str):
        """GET a URL and return its JSON, rate limited per request."""
        await self.rate_limiter.acquire()
        try:
            async with session.get(url) as response:
                return await response.json()
        finally:
            self.rate_limiter.release()
    
    def get_source_name(self) -> str:
        """Return source name."""
        return "hackernews"