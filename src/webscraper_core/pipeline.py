"""Orchestrator: URL -> fetch -> parse -> validate -> (export in Phase 3)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from webscraper_core.config import Settings, load_settings
from webscraper_core.exporters.obsidian import ObsidianExporter
from webscraper_core.fetchers.base import FetchResult
from webscraper_core.fetchers.router import looks_js_rendered, select_fetcher
from webscraper_core.llm.anthropic_client import LLMExtractor
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
        self.extractor = LLMExtractor(self.settings.llm)

    async def scrape_to_vault(
        self, url: str, task: str, *, force_dynamic: bool = False
    ) -> Path:
        """Full path: scrape then write the note into the vault. Returns the file path."""
        record = await self.run(url, task, force_dynamic=force_dynamic)
        return self.exporter.export(record)

    async def run(self, url: str, task: str, *, force_dynamic: bool = False) -> ScrapeRecord:
        parser = get_parser(task)  # validates task early

        result = await self._fetch(url, force_dynamic=force_dynamic)
        record = parser.parse(result)

        # Escalate to the dynamic fetcher when a static page looks JS-rendered.
        if record is None and not force_dynamic and looks_js_rendered(result):
            log.info("static under-rendered; escalating to dynamic fetch task=%s", task)
            try:
                dynamic_result = await self._fetch(url, force_dynamic=True)
            except ImportError:
                log.warning("dynamic fetch unavailable (install the 'dynamic' extra); skipping")
            else:
                result = dynamic_result
                record = parser.parse(result)

        if record is None:
            log.info("rule parse empty; trying llm_fallback task=%s", task)
            record = await parser.llm_fallback(result, self.extractor)
        if record is None:
            raise ScrapeError(f"no data extracted for task={task!r} at {url}")
        return record

    async def _fetch(self, url: str, *, force_dynamic: bool) -> FetchResult:
        fetcher = select_fetcher(self.settings, force_dynamic=force_dynamic)
        try:
            result = await fetcher.fetch(url)
        finally:
            await fetcher.aclose()
        log.info("fetched %s (%s) dynamic=%s", result.final_url, result.status, force_dynamic)
        return result

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
