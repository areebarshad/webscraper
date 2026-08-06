"""Article / news note schema."""

from __future__ import annotations

from datetime import date

from pydantic import Field, field_validator

from webscraper_core.schemas.base import ScrapeRecord


class ArticleNote(ScrapeRecord):
    note_kind: str = "article"

    title_text: str
    author: str | None = None
    published: date | None = None
    site: str | None = None
    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=lambda: ["article", "scraped"])

    @field_validator("title_text")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("article title must not be blank")
        return v

    def title(self) -> str:
        return self.title_text

    def frontmatter(self) -> dict[str, object]:
        fm: dict[str, object] = {
            "type": "article",
            "title": self.title_text,
            "source_url": self.source_url,
            "scraped_at": self.scraped_at,
            "tags": self.tags,
        }
        if self.author:
            fm["author"] = self.author
        if self.published:
            fm["published"] = self.published
        if self.site:
            fm["site"] = self.site
        return fm

    def body(self) -> str:
        meta_bits: list[str] = []
        if self.author:
            meta_bits.append(f"**Author:** [[{self.author}]]")
        if self.published:
            meta_bits.append(f"**Published:** {self.published.isoformat()}")
        source_label = self.site or self.source_url
        meta_bits.append(f"**Source:** [{source_label}]({self.source_url})")

        parts = [f"# {self.title_text}", "", "  ·  ".join(meta_bits), "", "---", "", self.content]
        return "\n".join(parts).rstrip() + "\n"
