"""Router: static-vs-dynamic heuristic + fetcher selection."""

from __future__ import annotations

from webscraper_core.config import Settings
from webscraper_core.fetchers.base import FetchResult
from webscraper_core.fetchers.router import looks_js_rendered, select_fetcher
from webscraper_core.fetchers.static import HttpxFetcher


def _res(html: str) -> FetchResult:
    return FetchResult(url="https://x.com", final_url="https://x.com", status=200, html=html)


def test_content_rich_page_is_not_js() -> None:
    assert looks_js_rendered(_res("<body>" + "word " * 200 + "</body>")) is False


def test_empty_spa_shell_is_js() -> None:
    assert looks_js_rendered(_res('<body><div id="root"></div></body>')) is True


def test_near_empty_body_is_js() -> None:
    assert looks_js_rendered(_res("<body><p>Loading...</p></body>")) is True


def test_select_static_by_default() -> None:
    assert isinstance(select_fetcher(Settings()), HttpxFetcher)
