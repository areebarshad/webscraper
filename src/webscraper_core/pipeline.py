"""Orchestrator: URL -> fetch -> parse -> validate -> (export in Phase 3)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from webscraper_core.config import Settings, load_settings
from webscraper_core.exporters.obsidian import ObsidianExporter
from webscraper_core.fetchers.router import select_fetcher
from webscraper_core.parsers.registry import get_parser
from webscraper_core.schemas.base import ScrapeRecord
from webscraper_core.utils.logging import get_logger

log = get_logger(__name__)


class ScrapeError(RuntimeError):
    """Raised when a URL cannot be turned into a validated record."""


class Pipeline:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.exporter = ObsidianExporter(self.settings)

    async def scrape_to_vault(
        self, url: str, task: str, *, force_dynamic: bool = False
    ) -> Path:
        """Full path: scrape then write the note into the vault. Returns the file path."""
        record = await self.run(url, task, force_dynamic=force_dynamic)
        return self.exporter.export(record)

    async def run(self, url: str, task: str, *, force_dynamic: bool = False) -> ScrapeRecord:
        parser = get_parser(task)  # validates task early
        fetcher = select_fetcher(self.settings, force_dynamic=force_dynamic)
        try:
            result = await fetcher.fetch(url)
        finally:
            await fetcher.aclose()

        log.info("fetched %s (%s) task=%s", result.final_url, result.status, task)

        record = parser.parse(result)
        if record is None:
            log.info("rule parse empty; trying llm_fallback task=%s", task)
            record = parser.llm_fallback(result)
        if record is None:
            raise ScrapeError(f"no data extracted for task={task!r} at {url}")
        return record

    async def run_many(
        self, urls: list[str], task: str, *, concurrency: int = 5, force_dynamic: bool = False
    ) -> list[ScrapeRecord | Exception]:
        """Scrape many URLs with bounded concurrency; failures returned inline."""
        sem = asyncio.Semaphore(concurrency)

        async def _one(u: str) -> ScrapeRecord | Exception:
            async with sem:
                try:
                    return await self.run(u, task, force_dynamic=force_dynamic)
                except Exception as exc:  # noqa: BLE001  (collected, not swallowed)
                    log.warning("scrape failed url=%s: %s", u, exc)
                    return exc

        return await asyncio.gather(*(_one(u) for u in urls))
