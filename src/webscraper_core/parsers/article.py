"""Article parser: trafilatura for clean content + metadata, selectolax for fallbacks."""

from __future__ import annotations

from contextlib import suppress
from datetime import date
from urllib.parse import urlsplit

import trafilatura
from selectolax.parser import HTMLParser

from webscraper_core.fetchers.base import FetchResult
from webscraper_core.parsers.base import BaseParser
from webscraper_core.schemas.article import ArticleNote

_MIN_CONTENT = 200  # chars; below this we treat extraction as failed


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    with suppress(ValueError):
        return date.fromisoformat(raw[:10])
    return None


class ArticleParser(BaseParser):
    task = "article"
    engine = "trafilatura"

    def parse(self, res: FetchResult) -> ArticleNote | None:
        content = trafilatura.extract(
            res.html,
            url=res.final_url,
            favor_recall=True,
            include_comments=False,
            include_tables=False,
        )
        if not content or len(content) < _MIN_CONTENT:
            return None

        meta = trafilatura.extract_metadata(res.html, default_url=res.final_url)
        title = getattr(meta, "title", None)
        author = getattr(meta, "author", None)
        pub_raw = getattr(meta, "date", None)

        if not title:
            title = self._title_from_html(res.html)
        if not title:
            return None

        return ArticleNote(
            source_url=res.final_url,
            title_text=title,
            author=author or None,
            published=_parse_date(pub_raw),
            site=urlsplit(res.final_url).netloc or None,
            content=content,
        )

    @staticmethod
    def _title_from_html(html: str) -> str | None:
        tree = HTMLParser(html)
        for sel in ("h1", "title"):
            node = tree.css_first(sel)
            if node and node.text(strip=True):
                return node.text(strip=True)
        return None
