# src/main.py

from src.orchestrator import FetchOrchestrator
from src.factories.fetcher_factory import FetcherFactory
from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage


async def main():
    """Main entry point with dependency injection."""
    
    # Create dependencies
    transformer = ArticleTransformer()
    storage = MarkdownStorage("data/articles")
    
    # Create fetchers via factory
    fetchers = [
        FetcherFactory.create("hackernews", transformer, storage),
        FetcherFactory.create(
            "rss", transformer, storage, feed_url="https://hnrss.org/frontpage"
        ),
        FetcherFactory.create("github", transformer, storage),
    ]
    
    # Inject dependencies into orchestrator
    orchestrator = FetchOrchestrator(
        fetchers=fetchers,
        storage=storage
    )
    
    # Run
    articles = await orchestrator.fetch_all()
    print(f"✅ Fetched {len(articles)} articles total")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())