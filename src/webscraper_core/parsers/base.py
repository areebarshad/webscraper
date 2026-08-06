"""Parser abstraction with an LLM fallback hook.

Each concrete parser declares:
  * ``task``   — registry key selecting it (e.g. "article", "contact").
  * ``engine`` — which HTML backend it uses; the router/parser reads accordingly.

``parse`` returns a validated ScrapeRecord, or ``None`` when it cannot extract
confidently. The pipeline then calls ``llm_fallback`` (a no-op until Phase 5).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Literal

from webscraper_core.fetchers.base import FetchResult
from webscraper_core.schemas.base import ScrapeRecord

if TYPE_CHECKING:
    from webscraper_core.llm.anthropic_client import LLMExtractor

Engine = Literal["selectolax", "bs4", "trafilatura"]


class BaseParser(ABC):
    task: ClassVar[str]
    engine: ClassVar[Engine]

    @abstractmethod
    def parse(self, res: FetchResult) -> ScrapeRecord | None:
        """Extract a record from HTML, or return None on low confidence."""

    async def llm_fallback(
        self, res: FetchResult, extractor: LLMExtractor
    ) -> ScrapeRecord | None:
        """Structured extraction via Claude when rule-based parse fails.

        Default no-op; subclasses that support it call ``extractor.extract``
        with a task-specific schema and map the result onto a note.
        """
        return None
