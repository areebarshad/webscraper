"""Fetcher selection + a heuristic for when a static page needs the dynamic path."""

from __future__ import annotations

from selectolax.parser import HTMLParser

from webscraper_core.config import Settings
from webscraper_core.fetchers.base import BaseFetcher, FetchResult
from webscraper_core.fetchers.static import HttpxFetcher

# Below this much visible text, a page is likely a JS shell that rendered nothing.
_THIN_TEXT = 500


def select_fetcher(settings: Settings, *, force_dynamic: bool = False) -> BaseFetcher:
    """Return the fetcher for this run. ``force_dynamic`` selects Playwright."""
    if force_dynamic:
        from webscraper_core.fetchers.dynamic import PlaywrightFetcher

        return PlaywrightFetcher(settings)
    return HttpxFetcher(settings)


def looks_js_rendered(res: FetchResult) -> bool:
    """True when a static fetch likely under-rendered a JS app.

    Signals: very little visible text, and a common SPA mount point / framework
    marker in the markup.
    """
    tree = HTMLParser(res.html)
    text = tree.body.text(separator=" ", strip=True) if tree.body else ""
    if len(text) >= _THIN_TEXT:
        return False
    markers = ("id=\"root\"", "id=\"app\"", "id=\"__next\"", "data-reactroot", "ng-app")
    lowered = res.html.lower()
    return any(m.lower() in lowered for m in markers) or len(text) < 50
