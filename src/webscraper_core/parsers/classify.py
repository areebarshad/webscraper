"""Lightweight, rule-based task classification for crawl's ``--task auto``.

Given a fetched page, decide which existing scrape task most likely fits, using
cheap structural signals (schema.org JSON-LD types and ``mailto:`` links) — no
LLM call. When nothing matches confidently it falls back to ``profile``, the most
permissive person/entity note type.

The result is always a real registered task, so the pipeline can hand it to
``get_parser`` directly.
"""

from __future__ import annotations

from selectolax.parser import HTMLParser

from webscraper_core.fetchers.base import FetchResult
from webscraper_core.utils.htmlclean import find_jsonld, mailto_addresses


def classify_task(res: FetchResult) -> str:
    """Best-guess task name for ``res`` among contact / profile."""
    tree = HTMLParser(res.html)

    # A person with reachable contact details -> a contact note.
    if mailto_addresses(tree) or find_jsonld(tree, "Person"):
        return "contact"

    return "profile"
