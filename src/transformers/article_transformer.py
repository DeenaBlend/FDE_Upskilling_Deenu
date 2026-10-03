"""Transform raw data to Article objects."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from dateutil import parser as date_parser
from src.models.article import Article


class ArticleTransformer:
    """
    Transforms raw data from various sources to Article objects.

    Single Responsibility: Data transformation only.
    """

    SUMMARY_MAX_LENGTH = 200

    def transform_hackernews(self, raw_data: List[Dict]) -> List[Article]:
        """
        Transform HackerNews API response to Articles.

        Items without a URL (Ask HN, deleted items, etc.) are skipped.

        Args:
            raw_data: List of HN items from API

        Returns:
            List of Article objects
        """
        articles = []

        for item in raw_data:
            # Skip if no URL (Ask HN, etc.) or deleted item (API returns null)
            if not item or not item.get("url"):
                continue

            try:
                article = Article(
                    title=item.get("title", "No Title"),
                    url=item["url"],
                    published_at=datetime.fromtimestamp(item.get("time", 0)),
                    source="hackernews",
                    summary=(item.get("text") or "")[: self.SUMMARY_MAX_LENGTH],
                    score=item.get("score", 0),
                )
            except Exception as e:
                print(f"⚠️  Failed to transform story {item.get('id')}: {e}")
                continue

            articles.append(article)

        return articles

    def transform_rss(self, entries: List[Any]) -> List[Article]:
        """
        Transform RSS feed entries to Articles.

        Entries without a link are skipped.

        Args:
            entries: List of RSS entries from feedparser

        Returns:
            List of Article objects
        """
        articles = []

        for entry in entries:
            url = entry.get("link", "")
            if not url:
                continue

            try:
                summary = entry.get("summary", entry.get("description", ""))
                article = Article(
                    title=entry.get("title", "No Title"),
                    url=url,
                    published_at=self._parse_date(
                        entry.get("published", entry.get("updated", ""))
                    ),
                    source="rss",
                    summary=self._strip_html(summary)[: self.SUMMARY_MAX_LENGTH],
                )
            except Exception as e:
                print(f"⚠️  Failed to parse entry: {e}")
                continue

            articles.append(article)

        return articles

    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """Parse various date formats, falling back to now if missing or invalid."""
        if not date_str:
            return datetime.now()

        try:
            return date_parser.parse(date_str)
        except (ValueError, OverflowError):
            return datetime.now()

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags (basic)."""
        return re.sub("<.*?>", "", text)
