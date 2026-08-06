"""Contact / person note schema."""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from webscraper_core.schemas.base import ScrapeRecord


class ContactNote(ScrapeRecord):
    note_kind: str = "contact"

    name: str
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    company: str | None = None
    socials: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=lambda: ["contact", "scraped"])

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("contact name must not be blank")
        return v

    @model_validator(mode="after")
    def _needs_some_signal(self) -> ContactNote:
        # A contact with only a name carries no usable data.
        if not (self.emails or self.phones or self.socials):
            raise ValueError("contact must have at least one email, phone, or social link")
        return self

    def title(self) -> str:
        return self.name

    def frontmatter(self) -> dict[str, object]:
        fm: dict[str, object] = {
            "type": "contact",
            "name": self.name,
            "source_url": self.source_url,
            "scraped_at": self.scraped_at,
            "tags": self.tags,
        }
        if self.emails:
            fm["emails"] = self.emails
        if self.phones:
            fm["phones"] = self.phones
        if self.company:
            fm["company"] = self.company
        if self.socials:
            fm["socials"] = self.socials
        return fm

    def body(self) -> str:
        lines = [f"# {self.name}", ""]
        if self.company:
            lines.append(f"**Company:** [[{self.company}]]")
        if self.emails:
            lines.append(f"**Email:** {', '.join(self.emails)}")
        if self.phones:
            lines.append(f"**Phone:** {', '.join(self.phones)}")
        if self.socials:
            lines += ["", "## Social"]
            lines += [f"- [{label}]({url})" for label, url in self.socials.items()]
        lines += ["", f"> Source: [{self.source_url}]({self.source_url})"]
        return "\n".join(lines).rstrip() + "\n"
