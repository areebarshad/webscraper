"""Lightweight, rule-based task classification for crawl's ``--task auto``.

Given a fetched page, decide which existing scrape task most likely fits, using
cheap structural signals (schema.org JSON-LD types, ``mailto:`` links, and the
amount of readable body text) — no LLM call. When nothing matches confidently it
falls back to ``profile``, the most permissive person/entity note type.

The result is always a real registered task, so the pipeline can hand it to
``get_parser`` directly.
"""

from __future__ import annotations

import trafilatura
from selectolax.parser import HTMLParser

from webscraper_core.fetchers.base import FetchResult
from webscraper_core.utils.htmlclean import find_jsonld, mailto_addresses

# schema.org @types that clearly indicate an article-like page.
_ARTICLE_TYPES = ("Article", "NewsArticle", "BlogPosting", "Report", "ScholarlyArticle")
# Readable-text length above which a page is treated as long-form (an article).
_ARTICLE_TEXT = 800


def classify_task(res: FetchResult) -> str:
    """Best-guess task name for ``res`` among article / contact / profile."""
    tree = HTMLParser(res.html)

    # A person with reachable contact details -> a contact note.
    if mailto_addresses(tree) or find_jsonld(tree, "Person"):
        return "contact"

    # Explicit article schema, or a lot of clean prose -> an article.
    if any(find_jsonld(tree, t) for t in _ARTICLE_TYPES):
        return "article"
    content = trafilatura.extract(res.html, favor_recall=False, include_comments=False)
    if content and len(content) >= _ARTICLE_TEXT:
        return "article"

    return "profile"
