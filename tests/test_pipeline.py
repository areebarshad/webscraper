"""Pipeline end-to-end tests with a stub fetcher (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from webscraper_core.config import Settings
from webscraper_core.fetchers.base import BaseFetcher, FetchResult
from webscraper_core.pipeline import Pipeline, ScrapeError
from webscraper_core.schemas.article import ArticleNote

FIXTURES = Path(__file__).parent / "fixtures"


class _StubFetcher(BaseFetcher):
    def __init__(self, html: str) -> None:
        self._html = html
        self.closed = False

    async def fetch(self, url: str) -> FetchResult:
        return FetchResult(url=url, final_url=url, status=200, html=self._html)

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def _patch_fetcher(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _StubFetcher((FIXTURES / "article.html").read_text(encoding="utf-8"))

    def _select(settings: Settings, *, force_dynamic: bool = False) -> BaseFetcher:
        return stub

    monkeypatch.setattr("webscraper_core.pipeline.select_fetcher", _select)
    # Keep tests hermetic: never fetch robots.txt over the network.
    async def _allowed(self, url):  # type: ignore[no-untyped-def]
        return True

    monkeypatch.setattr("webscraper_core.utils.robots.RobotsGate.allowed", _allowed)


async def test_pipeline_returns_article_record() -> None:
    record = await Pipeline(Settings()).run("https://news.example.com/x", "article")
    assert isinstance(record, ArticleNote)
    assert "Bakery" in record.title()


async def test_pipeline_raises_on_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    empty = _StubFetcher((FIXTURES / "empty.html").read_text(encoding="utf-8"))
    monkeypatch.setattr(
        "webscraper_core.pipeline.select_fetcher",
        lambda settings, *, force_dynamic=False: empty,
    )
    with pytest.raises(ScrapeError):
        await Pipeline(Settings()).run("https://spa.example.com", "article")


async def test_pipeline_unknown_task_raises() -> None:
    with pytest.raises(KeyError):
        await Pipeline(Settings()).run("https://x.com", "nope")
