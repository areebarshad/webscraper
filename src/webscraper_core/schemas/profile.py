"""Public-profile note schema (person profile pages)."""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from webscraper_core.schemas.base import ScrapeRecord


class ProfileNote(ScrapeRecord):
    note_kind: str = "profile"

    name: str
    headline: str | None = None
    bio: str | None = None
    location: str | None = None
    company: str | None = None
    emails: list[str] = Field(default_factory=list)
    socials: dict[str, str] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=lambda: ["profile", "scraped"])

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("profile name must not be blank")
        return v

    @model_validator(mode="after")
    def _needs_some_signal(self) -> ProfileNote:
        if not (self.headline or self.bio or self.socials or self.emails):
            raise ValueError("profile must have a headline, bio, social link, or email")
        return self

    def title(self) -> str:
        return self.name

    def frontmatter(self) -> dict[str, object]:
        fm: dict[str, object] = {
            "type": "profile",
            "name": self.name,
            "source_url": self.source_url,
            "scraped_at": self.scraped_at,
            "tags": self.tags,
        }
        for key in ("headline", "location", "company"):
            val = getattr(self, key)
            if val:
                fm[key] = val
        if self.emails:
            fm["emails"] = self.emails
        if self.socials:
            fm["socials"] = self.socials
        return fm

    def body(self) -> str:
        lines = [f"# {self.name}", ""]
        if self.headline:
            lines.append(f"*{self.headline}*")
            lines.append("")
        if self.company:
            lines.append(f"**Company:** [[{self.company}]]")
        if self.location:
            lines.append(f"**Location:** {self.location}")
        if self.emails:
            lines.append(f"**Email:** {', '.join(self.emails)}")
        if self.bio:
            lines += ["", "## Bio", "", self.bio]
        if self.socials:
            lines += ["", "## Social"]
            lines += [f"- [{label}]({url})" for label, url in self.socials.items()]
        lines += ["", f"> Source: [{self.source_url}]({self.source_url})"]
        return "\n".join(lines).rstrip() + "\n"
