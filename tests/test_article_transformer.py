# tests/test_article_transformer.py
"""Unit tests for ArticleTransformer (no network)."""
from datetime import datetime

import pytest

from src.transformers.article_transformer import ArticleTransformer


@pytest.fixture
def transformer():
    return ArticleTransformer()


# --- HackerNews -------------------------------------------------------------


def test_hackernews_maps_fields(transformer):
    raw = [{
        "id": 1,
        "title": "Show HN: Thing",
        "url": "https://example.com/thing",
        "time": 1_700_000_000,
        "score": 123,
        "text": "Some text",
    }]

    [article] = transformer.transform_hackernews(raw)

    assert article.title == "Show HN: Thing"
    assert article.url == "https://example.com/thing"
    assert article.published_at == datetime.fromtimestamp(1_700_000_000)
    assert article.source == "hackernews"
    assert article.summary == "Some text"
    assert article.score == 123


def test_hackernews_skips_items_without_url_and_deleted_items(transformer):
    raw = [
        None,  # deleted item (API returns null)
        {"id": 2, "title": "Ask HN: no url"},
        {"id": 3, "title": "Has url", "url": "https://example.com/3"},
    ]

    articles = transformer.transform_hackernews(raw)

    assert [a.title for a in articles] == ["Has url"]


def test_hackernews_defaults_for_missing_fields(transformer):
    [article] = transformer.transform_hackernews([{"url": "https://example.com"}])

    assert article.title == "No Title"
    assert article.score == 0
    assert article.summary == ""
    assert article.published_at == datetime.fromtimestamp(0)


def test_hackernews_handles_null_text(transformer):
    [article] = transformer.transform_hackernews(
        [{"title": "t", "url": "https://example.com", "text": None}]
    )
    assert article.summary == ""


def test_hackernews_truncates_summary(transformer):
    [article] = transformer.transform_hackernews(
        [{"title": "t", "url": "https://example.com", "text": "x" * 500}]
    )
    assert len(article.summary) == ArticleTransformer.SUMMARY_MAX_LENGTH


def test_hackernews_skips_items_that_fail_validation(transformer):
    raw = [
        {"id": 1, "title": "", "url": "https://example.com/empty-title"},
        {"id": 2, "title": "Bad time", "url": "https://example.com/bad", "time": "yesterday"},
        {"id": 3, "title": "Good", "url": "https://example.com/good"},
    ]

    articles = transformer.transform_hackernews(raw)

    assert [a.title for a in articles] == ["Good"]


def test_hackernews_empty_input(transformer):
    assert transformer.transform_hackernews([]) == []


# --- RSS --------------------------------------------------------------------


def test_rss_maps_fields(transformer):
    entries = [{
        "title": "RSS story",
        "link": "https://example.com/rss",
        "published": "Mon, 01 Jan 2024 10:30:00 GMT",
        "summary": "<p>Hello <b>world</b></p>",
    }]

    [article] = transformer.transform_rss(entries)

    assert article.title == "RSS story"
    assert article.url == "https://example.com/rss"
    assert article.source == "rss"
    assert article.summary == "Hello world"
    published = article.published_at
    assert (published.year, published.month, published.day, published.hour) == (2024, 1, 1, 10)


def test_rss_skips_entries_without_link(transformer):
    entries = [
        {"title": "no link"},
        {"title": "empty link", "link": ""},
        {"title": "ok", "link": "https://example.com"},
    ]
    assert [a.title for a in transformer.transform_rss(entries)] == ["ok"]


def test_rss_falls_back_to_description_and_updated(transformer):
    entries = [{
        "title": "t",
        "link": "https://example.com",
        "description": "From description",
        "updated": "2024-02-03T04:05:06",
    }]

    [article] = transformer.transform_rss(entries)

    assert article.summary == "From description"
    assert article.published_at == datetime(2024, 2, 3, 4, 5, 6)


def test_rss_truncates_summary_after_stripping_html(transformer):
    entries = [{
        "title": "t",
        "link": "https://example.com",
        "summary": "<div>" + "y" * 500 + "</div>",
    }]

    [article] = transformer.transform_rss(entries)

    assert article.summary == "y" * ArticleTransformer.SUMMARY_MAX_LENGTH


def test_rss_missing_date_uses_now(transformer):
    before = datetime.now()
    [article] = transformer.transform_rss([{"title": "t", "link": "https://example.com"}])
    assert before <= article.published_at <= datetime.now()


def test_rss_skips_entry_with_empty_title(transformer):
    entries = [
        {"title": "", "link": "https://example.com/a"},
        {"title": "ok", "link": "https://example.com/b"},
    ]
    assert [a.title for a in transformer.transform_rss(entries)] == ["ok"]


# --- Helpers ----------------------------------------------------------------


@pytest.mark.parametrize("value", [None, "", "garbage"])
def test_parse_date_falls_back_to_now(transformer, value):
    before = datetime.now()
    assert before <= transformer._parse_date(value) <= datetime.now()


def test_parse_date_parses_iso_string(transformer):
    assert transformer._parse_date("2024-05-06 07:08:09") == datetime(2024, 5, 6, 7, 8, 9)


def test_strip_html(transformer):
    assert transformer._strip_html('<a href="x">link</a> and <br/>text') == "link and text"
