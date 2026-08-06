"""Crawler integration tests with a fake fetcher (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from webscraper_core.config import Settings
from webscraper_core.crawler import Crawler
from webscraper_core.fetchers.base import FetchResult
from webscraper_core.pipeline import Pipeline
from webscraper_core.utils.robots import RobotsGate

SEED = "https://dept.edu/faculty"

_SEED_HTML = """
<html><body>
<h1>Physics Faculty</h1>
<nav><a href="/">Home</a></nav>
<main>
  <a href="/faculty/alice">Alice</a>
  <a href="/faculty/bob">Bob</a>
  <a href="https://twitter.com/dept">external</a>
</main>
</body></html>
"""

_PAGES = {
    SEED: _SEED_HTML,
    "https://dept.edu/faculty/alice": (
        '<html><body><h1>Alice Smith</h1>'
        '<a href="mailto:alice@dept.edu">email</a></body></html>'
    ),
    "https://dept.edu/faculty/bob": (
        '<html><body><h1>Bob Jones</h1>'
        '<a href="mailto:bob@dept.edu">email</a></body></html>'
    ),
}


async def _fake_fetch(url: str, *, force_dynamic: bool = False) -> FetchResult:
    html = _PAGES.get(url)
    if html is None:
        raise RuntimeError(f"unexpected fetch: {url}")
    return FetchResult(url=url, final_url=url, status=200, html=html)


def _pipeline(tmp_path: Path) -> Pipeline:
    pipeline = Pipeline(Settings(vault_path=tmp_path))  # type: ignore[arg-type]
    pipeline.robots = RobotsGate(enabled=False)  # keep tests offline
    pipeline._fetch = _fake_fetch  # type: ignore[method-assign,assignment]
    return pipeline


async def test_crawl_builds_hub_and_child_notes(tmp_path: Path) -> None:
    summary = await Crawler(_pipeline(tmp_path)).crawl(SEED, task="auto", depth=1)

    assert summary.hub_title == "Physics Faculty"
    assert set(summary.child_titles) == {"Alice Smith", "Bob Jones"}
    assert summary.hub_path is not None

    hub_text = summary.hub_path.read_text(encoding="utf-8")
    assert "[[Alice Smith]]" in hub_text
    assert "[[Bob Jones]]" in hub_text


async def test_child_notes_link_back_to_hub(tmp_path: Path) -> None:
    await Crawler(_pipeline(tmp_path)).crawl(SEED, task="auto", depth=1)
    alice = (tmp_path / "Contacts" / "Alice Smith.md").read_text(encoding="utf-8")
    assert "[[Physics Faculty]]" in alice  # parent frontmatter
    assert "> Part of [[Physics Faculty]]" in alice  # backlink section


async def test_crawl_stays_on_seed_domain(tmp_path: Path) -> None:
    summary = await Crawler(_pipeline(tmp_path)).crawl(SEED, task="auto", depth=1)
    assert all("twitter.com" not in u for u in summary.visited)


async def test_crawl_respects_max_pages(tmp_path: Path) -> None:
    summary = await Crawler(_pipeline(tmp_path)).crawl(
        SEED, task="auto", depth=1, max_pages=1
    )
    assert len(summary.child_paths) == 1


async def test_crawl_forced_task(tmp_path: Path) -> None:
    summary = await Crawler(_pipeline(tmp_path)).crawl(SEED, task="contact", depth=1)
    assert len(summary.child_paths) == 2


@pytest.mark.parametrize("depth", [1, 2])
async def test_crawl_no_children_when_leaves_are_empty(tmp_path: Path, depth: int) -> None:
    # A seed whose only link points at a page with no extractable data still
    # produces a hub note (with zero children), never crashing.
    pages = {
        "https://x.edu/root": '<html><body><h1>Root</h1><main>'
        '<a href="/empty">e</a></main></body></html>',
        "https://x.edu/empty": "<html><body><p>nothing here</p></body></html>",
    }

    async def fetch(url: str, *, force_dynamic: bool = False) -> FetchResult:
        return FetchResult(url=url, final_url=url, status=200, html=pages[url])

    pipeline = Pipeline(Settings(vault_path=tmp_path))  # type: ignore[arg-type]
    pipeline.robots = RobotsGate(enabled=False)
    pipeline._fetch = fetch  # type: ignore[method-assign,assignment]

    summary = await Crawler(pipeline).crawl("https://x.edu/root", task="auto", depth=depth)
    assert summary.hub_path is not None
    assert summary.child_paths == []
