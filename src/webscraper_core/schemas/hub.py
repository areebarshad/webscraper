"""Hub / map-of-content note schema.

The seed page of a ``crawl`` run becomes a hub note: a parent MOC that links out
to every child note harvested beneath it. Children link back via their
``parent`` field (see ``ScrapeRecord``), so the hub and its children form a
connected cluster in Obsidian's graph.
"""

from __future__ import annotations

from pydantic import Field, field_validator

from webscraper_core.schemas.base import ScrapeRecord


class HubNote(ScrapeRecord):
    note_kind: str = "hub"

    title_text: str
    summary: str | None = None
    seed_task: str | None = None  # the task used (or "auto") for child extraction
    children: list[str] = Field(default_factory=list)  # child note titles, in order
    tags: list[str] = Field(default_factory=lambda: ["hub", "moc", "scraped"])

    @field_validator("title_text")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("hub title must not be blank")
        return v

    def title(self) -> str:
        return self.title_text

    def frontmatter(self) -> dict[str, object]:
        fm: dict[str, object] = {
            "type": "hub",
            "title": self.title_text,
            "source_url": self.source_url,
            "scraped_at": self.scraped_at,
            "child_count": len(self.children),
            "tags": self.tags,
        }
        if self.seed_task:
            fm["seed_task"] = self.seed_task
        return fm

    def body(self) -> str:
        lines = [f"# {self.title_text}", ""]
        if self.summary:
            lines += [self.summary, ""]
        lines.append(f"## Contents ({len(self.children)})")
        lines.append("")
        if self.children:
            lines += [f"- [[{child}]]" for child in self.children]
        else:
            lines.append("_No child notes were harvested._")
        lines += ["", f"> Seed: [{self.source_url}]({self.source_url})"]
        return "\n".join(lines).rstrip() + "\n"
