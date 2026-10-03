"""Complete pipeline: Fetch -> Filter."""
import asyncio
from src.orchestrator import FetchOrchestrator
from src.factories.fetcher_factory import FetcherFactory
from src.transformers.article_transformer import ArticleTransformer
from src.storage.markdown_storage import MarkdownStorage
from src.agents.news_filter_agent import NewsFilterAgent
from pathlib import Path


async def run_pipeline():
    """
    Run complete pipeline.
    
    1. Fetch articles (Milestone 1)
    2. Filter with AI agent (Milestone 3)
    """
    print("=" * 60)
    print("  Complete Pipeline: Fetch + Filter")
    print("=" * 60)
    
    # Step 1: Fetch articles
    print("\n📰 Step 1: Fetching articles...")
    transformer = ArticleTransformer()
    storage = MarkdownStorage("data/articles")
    fetchers = [
        FetcherFactory.create("hackernews", transformer, storage),
        FetcherFactory.create(
            "rss", transformer, storage, feed_url="https://hnrss.org/frontpage"
        ),
        FetcherFactory.create("github", transformer, storage),
    ]
    orchestrator = FetchOrchestrator(fetchers=fetchers, storage=storage)
    articles = await orchestrator.fetch_all()
    
    fetch_output = Path("data/articles/all_articles.md")
    print(f"✅ Fetched {len(articles)} articles")
    print(f"   Saved to: {fetch_output}")
    
    # Step 2: Filter with AI
    print("\n🤖 Step 2: Filtering with AI...")
    agent = NewsFilterAgent()
    filter_output = Path("data/context/filtered_articles.md")
    
    result = await agent.execute(
        input_path=str(fetch_output),
        output_path=str(filter_output)
    )
    
    print(f"✅ Filtering complete")
    print(f"   Filtered articles: {filter_output}")
    
    print("\n" + "=" * 60)
    print("🎉 Pipeline complete!")
    print(f"   1. Fetched: {fetch_output}")
    print(f"   2. Filtered: {filter_output}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_pipeline())