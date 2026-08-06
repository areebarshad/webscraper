"""Recursive, multi-level domain crawler built on top of the single-page pipeline.

Starting from a seed URL, the crawler:

  1. fetches the seed and turns it into a **hub** map-of-content note;
  2. discovers in-content sub-links (see ``fetchers/discovery``);
  3. scrapes each discovered page into a child note — choosing the task per page
     when ``task="auto"`` (see ``parsers/classify``) — down to ``depth`` levels;
  4. wires every child back to the hub (``parent`` field -> frontmatter + backlink)
     and lists all children on the hub note.

Politeness and safety are inherited from the pipeline: the per-host throttle, UA
rotation, and retry backoff live in the fetchers, ``RobotsGate`` is honoured for
every URL, and a ``max_pages`` budget plus URL de-duplication bound every run so
the same page is never scraped twice.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from selectolax.parser import HTMLParser

from webscraper_core.fetchers.base import FetchResult
from webscraper_core.fetchers.discovery import _normalize, discover_links
from webscraper_core.parsers.classify import classify_task
from webscraper_core.pipeline import Pipeline
from webscraper_core.schemas.hub import HubNote
from webscraper_core.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class CrawlSummary:
    """Outcome of a crawl run, returned to the CLI for reporting."""

    hub_title: str
    hub_path: Path | None = None
    child_paths: list[Path] = field(default_factory=list)
    child_titles: list[str] = field(default_factory=list)
    visited: list[str] = field(default_factory=list)
    failures: list[tuple[str, str]] = field(default_factory=list)  # (url, reason)

    @property
    def written(self) -> int:
        return len(self.child_paths) + (1 if self.hub_path else 0)


@dataclass
class _PageOutcome:
    url: str
    path: Path | None = None
    title: str | None = None
    links: list[str] = field(default_factory=list)
    reason: str | None = None  # set when no note was written


def _derive_title(res: FetchResult) -> str:
    """A human hub title from the seed page: its <h1>, then <title>, then host."""
    tree = HTMLParser(res.html)
    for sel in ("h1", "title"):
        node = tree.css_first(sel)
        if node and node.text(strip=True):
            return node.text(strip=True)
    return urlsplit(res.final_url).netloc or "Crawl Hub"


class Crawler:
    """Drives a recursive crawl using a configured :class:`Pipeline`."""

    def __init__(self, pipeline: Pipeline) -> None:
        self.pipeline = pipeline

    async def crawl(
        self,
        seed: str,
        *,
        task: str = "auto",
        depth: int = 1,
        max_pages: int = 20,
        same_domain: bool = True,
        force_dynamic: bool = False,
        concurrency: int = 5,
    ) -> CrawlSummary:
        # --- seed: fetch and turn into the hub -------------------------------
        if not await self.pipeline.robots.allowed(seed):
            return CrawlSummary(
                hub_title=seed, failures=[(seed, "disallowed by robots.txt")]
            )
        seed_result = await self.pipeline._fetch(seed, force_dynamic=force_dynamic)
        hub_title = _derive_title(seed_result)

        visited: set[str] = {_normalize(seed_result.final_url), _normalize(seed)}
        summary = CrawlSummary(hub_title=hub_title)
        sem = asyncio.Semaphore(max(1, concurrency))
        budget = max(0, max_pages)

        # Level-0 discovery from the seed produces the first frontier.
        frontier = self._filter(
            discover_links(seed_result.html, seed_result.final_url, same_domain=same_domain),
            visited,
        )

        # --- BFS across `depth` levels of sub-links --------------------------
        for level in range(1, depth + 1):
            if not frontier or budget <= 0:
                break
            batch = frontier[:budget]
            budget -= len(batch)
            for url in batch:  # reserve so a link shared across pages isn't re-queued
                visited.add(_normalize(url))

            outcomes = await asyncio.gather(
                *(
                    self._process(
                        url,
                        hub_title=hub_title,
                        task=task,
                        discover_more=level < depth,
                        same_domain=same_domain,
                        force_dynamic=force_dynamic,
                        sem=sem,
                    )
                    for url in batch
                )
            )

            next_frontier: list[str] = []
            for outcome in outcomes:
                summary.visited.append(outcome.url)
                if outcome.path is not None and outcome.title is not None:
                    summary.child_paths.append(outcome.path)
                    summary.child_titles.append(outcome.title)
                else:
                    summary.failures.append((outcome.url, outcome.reason or "no data"))
                next_frontier += outcome.links
            frontier = self._filter(next_frontier, visited)

        # --- hub note: list every harvested child ----------------------------
        hub = HubNote(
            source_url=seed_result.final_url,
            title_text=hub_title,
            seed_task=task,
            children=summary.child_titles,
        )
        summary.hub_path = self.pipeline.exporter.export(hub)
        log.info(
            "crawl done seed=%s hub=%r children=%d visited=%d failures=%d",
            seed,
            hub_title,
            len(summary.child_paths),
            len(summary.visited),
            len(summary.failures),
        )
        return summary

    @staticmethod
    def _filter(urls: list[str], visited: set[str]) -> list[str]:
        """Drop already-seen URLs, order-preserving, deduping within the batch too."""
        out: list[str] = []
        local: set[str] = set()
        for url in urls:
            key = _normalize(url)
            if key in visited or key in local:
                continue
            local.add(key)
            out.append(url)
        return out

    async def _process(
        self,
        url: str,
        *,
        hub_title: str,
        task: str,
        discover_more: bool,
        same_domain: bool,
        force_dynamic: bool,
        sem: asyncio.Semaphore,
    ) -> _PageOutcome:
        """Fetch, (optionally) extract, and discover links for one child URL.

        Never raises: a single bad URL must not abort the crawl (golden rule 3).
        """
        async with sem:
            if not await self.pipeline.robots.allowed(url):
                return _PageOutcome(url=url, reason="disallowed by robots.txt")
            try:
                result = await self.pipeline._fetch(url, force_dynamic=force_dynamic)
            except Exception as exc:  # noqa: BLE001  (reported, not swallowed)
                log.warning("crawl fetch failed url=%s: %s", url, exc)
                return _PageOutcome(url=url, reason=f"fetch error: {exc}")

            page_task = task if task != "auto" else classify_task(result)
            try:
                result, record = await self.pipeline.extract(
                    url, result, page_task, force_dynamic=force_dynamic
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("crawl extract failed url=%s: %s", url, exc)
                record = None

            links = (
                discover_links(result.html, result.final_url, same_domain=same_domain)
                if discover_more
                else []
            )
            if record is None:
                return _PageOutcome(url=url, links=links, reason="no data extracted")

            record.parent = hub_title
            path = self.pipeline.exporter.export(record)
            return _PageOutcome(url=url, path=path, title=record.title(), links=links)
