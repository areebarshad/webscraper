"""Exporters: write a ScrapeRecord to a destination (Obsidian vault)."""

from webscraper_core.exporters.base import BaseExporter
from webscraper_core.exporters.obsidian import ObsidianExporter

__all__ = ["BaseExporter", "ObsidianExporter"]
