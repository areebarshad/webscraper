"""LLM fallback tests — offline, using a fake extractor (no Anthropic calls)."""

from __future__ import annotations

from pydantic import BaseModel

from webscraper_core.config import LLMSettings
from webscraper_core.fetchers.base import FetchResult
from webscraper_core.llm.anthropic_client import LLMExtractor
from webscraper_core.parsers.article import ArticleParser
from webscraper_core.parsers.contact import ContactParser
from webscraper_core.parsers.profile import ProfileParser
from webscraper_core.schemas.article import ArticleNote
from webscraper_core.schemas.contact import ContactNote
from webscraper_core.schemas.llm import LLMArticle, LLMContact, LLMProfile
from webscraper_core.schemas.profile import ProfileNote


def _res() -> FetchResult:
    return FetchResult(
        url="https://x.com/p",
        final_url="https://x.com/p",
        status=200,
        html="<html><body>irregular</body></html>",
    )


class _FakeExtractor:
    """Returns a preset object for whichever schema the parser requests."""

    def __init__(self, payload: dict[type, BaseModel | None]) -> None:
        self._payload = payload

    async def extract(self, res, schema, instruction):  # type: ignore[no-untyped-def]
        return self._payload.get(schema)


async def test_extractor_disabled_returns_none() -> None:
    extractor = LLMExtractor(LLMSettings(enabled=False))
    assert extractor.enabled is False
    assert await extractor.extract(_res(), LLMArticle, "x") is None


async def test_article_llm_fallback_maps_note() -> None:
    fake = _FakeExtractor(
        {LLMArticle: LLMArticle(title="Deep Dive", author="Ann", published="2026-01-02",
                                content="Body " * 60)}
    )
    note = await ArticleParser().llm_fallback(_res(), fake)  # type: ignore[arg-type]
    assert isinstance(note, ArticleNote)
    assert note.title_text == "Deep Dive"
    assert note.author == "Ann"
    assert note.published is not None and note.published.year == 2026


async def test_article_llm_fallback_empty_content_returns_none() -> None:
    fake = _FakeExtractor({LLMArticle: LLMArticle(title="X", content="   ")})
    assert await ArticleParser().llm_fallback(_res(), fake) is None  # type: ignore[arg-type]


async def test_contact_llm_fallback_maps_socials() -> None:
    fake = _FakeExtractor(
        {LLMContact: LLMContact(name="Jane", emails=["j@a.com"],
                                linkedin="https://linkedin.com/in/jane")}
    )
    note = await ContactParser().llm_fallback(_res(), fake)  # type: ignore[arg-type]
    assert isinstance(note, ContactNote)
    assert note.socials["linkedin"].endswith("/jane")


async def test_contact_llm_fallback_no_signal_returns_none() -> None:
    fake = _FakeExtractor({LLMContact: LLMContact(name="Jane")})
    assert await ContactParser().llm_fallback(_res(), fake) is None  # type: ignore[arg-type]


async def test_profile_llm_fallback_maps_note() -> None:
    fake = _FakeExtractor(
        {LLMProfile: LLMProfile(name="Jane", headline="Engineer", bio="Builds things")}
    )
    note = await ProfileParser().llm_fallback(_res(), fake)  # type: ignore[arg-type]
    assert isinstance(note, ProfileNote)
    assert note.headline == "Engineer"


async def test_llm_fallback_returns_none_when_extractor_yields_nothing() -> None:
    fake = _FakeExtractor({})  # extract() returns None for every schema
    assert await ArticleParser().llm_fallback(_res(), fake) is None  # type: ignore[arg-type]
