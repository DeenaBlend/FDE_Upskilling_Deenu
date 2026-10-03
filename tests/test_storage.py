# tests/test_storage.py
from src.storage.base_storage import ArticleStorage
from src.storage.markdown_storage import MarkdownStorage
from src.models.article import Article
from datetime import datetime
import re
import tempfile


def _article(title="Sample story", **overrides):
    fields = {
        "title": title,
        "url": "https://example.com/story",
        "published_at": datetime(2026, 1, 1, 12, 0),
        "source": "test",
    }
    return Article(**{**fields, **overrides})


def test_storage_save():
    """Test saving articles."""
    # Use temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = MarkdownStorage(tmpdir)

        article = Article(
            title="Test",
            url="https://test.com",
            published_at=datetime.now(),
            source="test",
        )

        path = storage.save([article], "test.md")

        assert path.exists()
        content = path.read_text()
        assert "Test" in content


def test_storage_multiple_articles():
    """Test saving multiple articles."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = MarkdownStorage(tmpdir)

        articles = [
            Article(f"Article {i}", f"https://test{i}.com", datetime.now(), "test")
            for i in range(5)
        ]

        path = storage.save(articles)
        content = path.read_text()

        assert "Article 0" in content
        assert "Article 4" in content


def test_storage_creates_nested_directory(tmp_path):
    """Constructor creates the base directory, including parents."""
    base = tmp_path / "nested" / "dir"
    MarkdownStorage(str(base))
    assert base.is_dir()


def test_storage_implements_interface(tmp_path):
    assert isinstance(MarkdownStorage(str(tmp_path)), ArticleStorage)


def test_storage_auto_generated_filename(tmp_path):
    """No filename -> timestamped articles_YYYY-MM-DD_HH-MM.md in base dir."""
    path = MarkdownStorage(str(tmp_path)).save([_article()])

    assert path.parent == tmp_path
    assert re.fullmatch(r"articles_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.md", path.name)


def test_storage_header_and_separators(tmp_path):
    path = MarkdownStorage(str(tmp_path)).save(
        [_article("First story"), _article("Second story")], "out.md"
    )
    content = path.read_text(encoding="utf-8")

    assert content.startswith("# News Articles\n")
    assert "**Total Articles:** 2" in content
    # One separator after the header, one after each article
    assert content.count("\n---\n") == 3


def test_storage_empty_list(tmp_path):
    content = MarkdownStorage(str(tmp_path)).save([], "empty.md").read_text()

    assert "**Total Articles:** 0" in content
    assert "## " not in content


def test_storage_overwrites_existing_file(tmp_path):
    storage = MarkdownStorage(str(tmp_path))
    storage.save([_article("First story")], "same.md")

    content = storage.save([_article("Second story")], "same.md").read_text()

    assert "Second story" in content
    assert "First story" not in content


def test_storage_writes_unicode(tmp_path):
    title = "Café ☕ – naïve résumé"
    path = MarkdownStorage(str(tmp_path)).save([_article(title)], "unicode.md")
    assert title in path.read_text(encoding="utf-8")
