"""Lean Pydantic schemas for Claude structured-output extraction.

These are intentionally flat and free of validation constraints the structured-
output JSON schema can't express (min_length, arbitrary-key dicts). Parsers map
the extracted result onto the richer note schemas, filling source_url etc.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LLMArticle(BaseModel):
    title: str = Field(description="The article headline.")
    author: str | None = Field(default=None, description="Author name, if stated.")
    published: str | None = Field(
        default=None, description="Publication date as ISO 8601 (YYYY-MM-DD), if stated."
    )
    content: str = Field(description="The clean article body text, as Markdown.")


class LLMContact(BaseModel):
    name: str = Field(description="The person's full name.")
    emails: list[str] = Field(default_factory=list, description="Email addresses.")
    phones: list[str] = Field(default_factory=list, description="Phone numbers.")
    company: str | None = Field(default=None, description="Employer or organization.")
    linkedin: str | None = Field(default=None, description="LinkedIn profile URL.")
    twitter: str | None = Field(default=None, description="Twitter/X profile URL.")
    github: str | None = Field(default=None, description="GitHub profile URL.")


class LLMProfile(BaseModel):
    name: str = Field(description="The person's full name.")
    headline: str | None = Field(default=None, description="Role or one-line headline.")
    bio: str | None = Field(default=None, description="Short biography.")
    location: str | None = Field(default=None, description="Location, if stated.")
    company: str | None = Field(default=None, description="Employer or organization.")
    emails: list[str] = Field(default_factory=list, description="Email addresses.")


class LLMResearchItem(BaseModel):
    title: str = Field(description="Title of the paper, project, or publication.")
    url: str | None = Field(default=None, description="Link to the source, if present.")
    year: int | None = Field(default=None, description="Year of publication, if stated.")
    venue: str | None = Field(
        default=None, description="Journal, conference, or publisher, if stated."
    )
    summary: str | None = Field(default=None, description="One-line summary, if available.")


class LLMResearch(BaseModel):
    name: str = Field(description="The researcher's full name.")
    affiliation: str | None = Field(
        default=None, description="University, department, or organization."
    )
    items: list[LLMResearchItem] = Field(
        default_factory=list, description="Every distinct publication or research work found."
    )
