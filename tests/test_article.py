# tests/test_article.py
from src.models.article import Article
from datetime import datetime
import pytest


def test_article_creation():
    """Test creating article."""
    article = Article(
        title="Test", url="https://test.com", published_at=datetime.now(), source="test"
    )
    assert article.title == "Test"
    assert article.url == "https://test.com"


def test_article_validation():
    """Test article validation."""
    with pytest.raises(ValueError):
        Article(
            title="",  # Empty title should fail
            url="https://test.com",
            published_at=datetime.now(),
            source="test",
        )


def test_article_to_markdown():
    """Test markdown conversion."""
    article = Article(
        title="Test Article",
        url="https://test.com",
        published_at=datetime.now(),
        source="test",
        summary="Test summary",
    )

    md = article.to_markdown()
    assert "Test Article" in md
    assert "https://test.com" in md
    assert "test" in md


def test_article_defaults(sample_article_kwargs):
    """Optional fields default to empty summary and zero score."""
    article = Article(**sample_article_kwargs)
    assert article.summary == ""
    assert article.score == 0


def test_article_missing_url(sample_article_kwargs):
    """Empty URL should fail with a URL-specific message."""
    with pytest.raises(ValueError, match="URL"):
        Article(**{**sample_article_kwargs, "url": ""})


def test_article_to_markdown_format(sample_article_kwargs):
    """Every field lands in the markdown in the expected format."""
    article = Article(**sample_article_kwargs, summary="A short summary", score=42)

    md = article.to_markdown()

    assert md.startswith("## Sample article for tests\n")
    assert "**Source:** test" in md
    assert "**URL:** https://example.com/sample" in md
    assert "**Published:** 2026-01-01 12:00" in md
    assert "**Score:** 42" in md
    assert md.rstrip().endswith("A short summary")


def test_article_equality(sample_article_kwargs):
    """Dataclass equality compares field values."""
    assert Article(**sample_article_kwargs) == Article(**sample_article_kwargs)
