"""Base record shared by every scraped note type."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


class ScrapeRecord(BaseModel):
    """Common fields every exportable record carries.

    Subclasses (ContactNote, ProfileNote, ...) add task-specific fields and set
    ``note_kind``. The exporter relies only on this base plus each subclass's
    ``title()`` / ``frontmatter()`` / ``body()`` contract.
    """

    model_config = ConfigDict(extra="forbid")

    note_kind: str  # e.g. "contact", "profile"; also drives the vault subdir
    source_url: str
    scraped_at: datetime = Field(default_factory=_utcnow)

    # Set by the crawler when this note was discovered under a hub/seed page. The
    # exporter injects a ``parent: "[[Hub]]"`` frontmatter key and a backlink
    # section, so every note type gains parent linkage without touching its own
    # frontmatter()/body(). Left None for standalone scrapes.
    parent: str | None = Field(default=None, exclude=True)

    def title(self) -> str:
        """Human title used to build the note filename. Overridden by subclasses."""
        raise NotImplementedError

    def frontmatter(self) -> dict[str, object]:
        """Mapping serialized to YAML frontmatter. Overridden by subclasses."""
        raise NotImplementedError

    def body(self) -> str:
        """Markdown body (without frontmatter). Overridden by subclasses."""
        raise NotImplementedError
