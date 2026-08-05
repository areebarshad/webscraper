"""Base record shared by every scraped note type."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ScrapeRecord(BaseModel):
    """Common fields every exportable record carries.

    Subclasses (ArticleNote, ContactNote, ...) add task-specific fields and set
    ``note_kind``. The exporter relies only on this base plus each subclass's
    ``title()`` / ``frontmatter()`` / ``body()`` contract.
    """

    model_config = ConfigDict(extra="forbid")

    note_kind: str  # e.g. "article", "contact"; also drives the vault subdir
    source_url: str
    scraped_at: datetime = Field(default_factory=_utcnow)

    def title(self) -> str:
        """Human title used to build the note filename. Overridden by subclasses."""
        raise NotImplementedError

    def frontmatter(self) -> dict[str, object]:
        """Mapping serialized to YAML frontmatter. Overridden by subclasses."""
        raise NotImplementedError

    def body(self) -> str:
        """Markdown body (without frontmatter). Overridden by subclasses."""
        raise NotImplementedError
