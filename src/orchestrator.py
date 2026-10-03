# src/orchestrator.py

import asyncio
from typing import List
from src.models.article import Article
from src.fetchers.base_fetcher import BaseFetcher
from src.storage.base_storage import ArticleStorage


class FetchOrchestrator:
    """
    Orchestrates multiple fetchers.
    
    Follows Dependency Inversion Principle:
    - Depends on abstractions (BaseFetcher, ArticleStorage)
    - Dependencies injected via constructor
    """
    
    def __init__(
        self,
        fetchers: List[BaseFetcher],
        storage: ArticleStorage
    ):
        """
        Initialize with injected dependencies.
        
        Args:
            fetchers: List of fetcher instances
            storage: Storage implementation (saves the combined results)
        """
        self.fetchers = fetchers
        self.storage = storage
    
    async def fetch_all(self) -> List[Article]:
        """Fetch from all sources concurrently and save the combined results."""
        # Fetch from all sources at the same time
        results = await asyncio.gather(
            *(fetcher.fetch_and_save() for fetcher in self.fetchers),
            return_exceptions=True,
        )

        all_articles = []
        
        for fetcher, result in zip(self.fetchers, results):
            if isinstance(result, Exception):
                print(f"⚠️  {fetcher.get_source_name()} failed: {result}")
                continue
            all_articles.extend(result)
        
        # Save combined results
        if all_articles:
            self.storage.save(all_articles, "all_articles.md")

        return all_articles