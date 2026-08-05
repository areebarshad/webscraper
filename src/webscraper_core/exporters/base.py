"""Exporter abstraction: persist a validated record, return the written path."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from webscraper_core.schemas.base import ScrapeRecord


class BaseExporter(ABC):
    @abstractmethod
    def export(self, record: ScrapeRecord) -> Path:
        """Write ``record`` and return the path of the created/updated file."""
