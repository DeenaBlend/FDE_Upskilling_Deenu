# tests/test_db_manager.py
"""Tests for DatabaseManager using a throwaway SQLite file under tmp_path."""
import pytest

from src.database.db_manager import DatabaseManager


def _row(n, source="hackernews", published="2026-01-01T00:00:00", **extra):
    return {
        "title": f"Article {n}",
        "url": f"https://example.com/{n}",
        "source": source,
        "published_at": published,
        **extra,
    }


@pytest.fixture
def db(tmp_path):
    return DatabaseManager(str(tmp_path / "db" / "test.db"))


def test_init_creates_parent_directory(tmp_path):
    DatabaseManager(str(tmp_path / "nested" / "news.db"))
    assert (tmp_path / "nested").is_dir()


@pytest.mark.asyncio
async def test_initialize_is_idempotent(db):
    await db.initialize()
    await db.initialize()

    assert await db.query_articles() == []


@pytest.mark.asyncio
async def test_insert_and_query_with_defaults(db):
    await db.initialize()
    await db.insert_article(_row(1))

    [row] = await db.query_articles()

    assert row["id"] == 1
    assert row["title"] == "Article 1"
    assert row["url"] == "https://example.com/1"
    assert row["source"] == "hackernews"
    assert row["summary"] == ""
    assert row["score"] == 0
    assert row["relevance_score"] == 0
    assert row["created_at"]


@pytest.mark.asyncio
async def test_insert_stores_optional_fields(db):
    await db.initialize()
    await db.insert_article(_row(1, summary="About LLMs", score=42, relevance_score=8))

    [row] = await db.query_articles()

    assert (row["summary"], row["score"], row["relevance_score"]) == ("About LLMs", 42, 8)


@pytest.mark.asyncio
async def test_duplicate_url_is_ignored(db):
    await db.initialize()
    await db.insert_article(_row(1))
    await db.insert_article({**_row(1), "title": "Different title"})

    rows = await db.query_articles()

    assert [r["title"] for r in rows] == ["Article 1"]


@pytest.mark.asyncio
async def test_query_filters_by_source(db):
    await db.initialize()
    await db.insert_article(_row(1, source="hackernews"))
    await db.insert_article(_row(2, source="rss"))
    await db.insert_article(_row(3, source="rss"))

    rows = await db.query_articles(source="rss")

    assert sorted(r["title"] for r in rows) == ["Article 2", "Article 3"]


@pytest.mark.asyncio
async def test_query_orders_newest_first_and_limits(db):
    await db.initialize()
    for n, day in [(1, "01"), (2, "03"), (3, "02")]:
        await db.insert_article(_row(n, published=f"2026-01-{day}T00:00:00"))

    rows = await db.query_articles(limit=2)

    assert [r["title"] for r in rows] == ["Article 2", "Article 3"]


@pytest.mark.asyncio
async def test_insert_missing_required_field_raises(db):
    await db.initialize()
    with pytest.raises(KeyError):
        await db.insert_article({"title": "No url"})
