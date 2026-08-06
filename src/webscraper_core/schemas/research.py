"""Research note schema: a person's body of research with source links.

Companion to the contact note — scraping "Professor X" yields a contact note
(email, department, phone) and a research note listing their publications, each
with a link back to where it was found. The two link via a shared `[[Name]]`.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator, model_validator

from webscraper_core.schemas.base import ScrapeRecord

# A bare hostname (lowercase, dotted, no spaces) — not an institution to link.
# "en.wikipedia.org" matches; "N.Y.U." / "University of Example" do not.
_DOMAINISH = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")


class ResearchItem(BaseModel):
    title: str
    url: str | None = None
    year: int | None = None
    venue: str | None = None
    summary: str | None = None

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("research item title must not be blank")
        return v


class ResearchNote(ScrapeRecord):
    note_kind: str = "research"

    name: str
    affiliation: str | None = None
    items: list[ResearchItem] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=lambda: ["research", "scraped"])

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("research name must not be blank")
        return v

    @model_validator(mode="after")
    def _needs_items(self) -> ResearchNote:
        if not self.items:
            raise ValueError("research note must contain at least one item")
        return self

    def title(self) -> str:
        # Distinct filename so a person's research note doesn't collide with
        # their contact note when both dirs are browsed together.
        return f"{self.name} - Research"

    def frontmatter(self) -> dict[str, object]:
        fm: dict[str, object] = {
            "type": "research",
            "name": self.name,
            "source_url": self.source_url,
            "scraped_at": self.scraped_at,
            "item_count": len(self.items),
            "tags": self.tags,
        }
        if self.affiliation:
            fm["affiliation"] = self.affiliation
        return fm

    def body(self) -> str:
        lines = [f"# {self.name} — Research", ""]
        lines.append(f"Research by [[{self.name}]]")  # links back to the contact note
        if self.affiliation:
            # Wikilink a real org name (an institution hub); leave a bare domain plain.
            aff = self.affiliation
            label = aff if _DOMAINISH.match(aff) else f"[[{aff}]]"
            lines.append(f"**Affiliation:** {label}")
        lines += ["", f"## Publications ({len(self.items)})", ""]
        for item in self.items:
            meta = " · ".join(
                bit for bit in (item.venue, str(item.year) if item.year else None) if bit
            )
            heading = f"[{item.title}]({item.url})" if item.url else item.title
            lines.append(f"- {heading}" + (f" — *{meta}*" if meta else ""))
            if item.summary:
                lines.append(f"  - {item.summary}")
        lines += ["", f"> Source: [{self.source_url}]({self.source_url})"]
        return "\n".join(lines).rstrip() + "\n"
