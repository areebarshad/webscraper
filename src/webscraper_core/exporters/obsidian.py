"""Obsidian exporter: render a record to a Markdown note and write it into the vault."""

from __future__ import annotations

from pathlib import Path

import yaml

from webscraper_core.config import Settings
from webscraper_core.exporters.base import BaseExporter
from webscraper_core.schemas.base import ScrapeRecord
from webscraper_core.utils.logging import get_logger
from webscraper_core.utils.sanitize import sanitize_filename, unique_path

log = get_logger(__name__)


def render_frontmatter(data: dict[str, object]) -> str:
    """YAML frontmatter block. safe_dump handles quoting/dates so titles with
    colons, quotes, or newlines can never break the block."""
    dumped = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    return f"---\n{dumped}---\n"


def render_note(record: ScrapeRecord) -> str:
    fm = record.frontmatter()
    body = record.body()
    # Crawler-set parent: wire the note back to its hub in both frontmatter (for
    # dataview/queries) and the body (a visible backlink in Obsidian's graph).
    if record.parent:
        fm = {**fm, "parent": f"[[{record.parent}]]"}
        body = body.rstrip() + f"\n\n---\n\n> Part of [[{record.parent}]]\n"
    return render_frontmatter(fm) + "\n" + body


class ObsidianExporter(BaseExporter):
    """Write records as `.md` notes into vault subdirs chosen by ``note_kind``."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._subdirs = {
            "article": settings.articles_dir,
            "contact": settings.contacts_dir,
            "profile": settings.profiles_dir,
            "research": settings.research_dir,
            "hub": settings.hub_dir,
        }

    def _target_dir(self, record: ScrapeRecord) -> Path:
        subdir = self._subdirs.get(record.note_kind, record.note_kind.capitalize())
        return self.settings.vault_path / subdir

    def export(self, record: ScrapeRecord) -> Path:
        directory = self._target_dir(record)
        directory.mkdir(parents=True, exist_ok=True)

        stem = sanitize_filename(record.title(), fallback_seed=record.source_url)
        if self.settings.overwrite_existing:
            path = directory / f"{stem}.md"
        else:
            path = unique_path(directory, stem)

        path.write_text(render_note(record), encoding="utf-8")
        log.info("wrote %s note -> %s", record.note_kind, path)
        return path
