"""Fetcher selection. Phase 2 is static-only; Phase 4 adds the dynamic path."""

from __future__ import annotations

from webscraper_core.config import Settings
from webscraper_core.fetchers.base import BaseFetcher
from webscraper_core.fetchers.static import HttpxFetcher


def select_fetcher(settings: Settings, *, force_dynamic: bool = False) -> BaseFetcher:
    """Return the fetcher for this run.

    ``force_dynamic`` is accepted now so the CLI contract is stable; the
    Playwright fetcher is wired here in Phase 4.
    """
    if force_dynamic:
        raise NotImplementedError("dynamic (Playwright) fetching arrives in Phase 4")
    return HttpxFetcher(settings)
