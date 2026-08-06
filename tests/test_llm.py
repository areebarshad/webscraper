"""LLM fallback tests — offline, using a fake extractor (no Anthropic calls)."""

from __future__ import annotations

from pydantic import BaseModel

from webscraper_core.config import LLMSettings
from webscraper_core.fetchers.base import FetchResult
from webscraper_core.llm.anthropic_client import LLMExtractor
from webscraper_core.parsers.contact import ContactParser
from webscraper_core.parsers.profile import ProfileParser
from webscraper_core.parsers.research import ResearchParser
from webscraper_core.schemas.contact import ContactNote
from webscraper_core.schemas.llm import (
    LLMContact,
    LLMProfile,
    LLMResearch,
    LLMResearchItem,
)
from webscraper_core.schemas.profile import ProfileNote
from webscraper_core.schemas.research import ResearchNote


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
    assert await extractor.extract(_res(), LLMContact, "x") is None


async def test_extractor_skips_short_pages_without_calling_api(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    # Enabled + key present, but the page is a near-empty shell: the gate must
    # skip the API call entirely (no client is ever constructed).
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-used")
    extractor = LLMExtractor(LLMSettings(enabled=True, min_chars=400))
    assert extractor.enabled is True
    tiny = FetchResult(
        url="https://x.com", final_url="https://x.com", status=200,
        html="<html><body><div id='app'></div><p>Loading...</p></body></html>",
    )
    assert await extractor.extract(tiny, LLMContact, "x") is None
    assert extractor._client is None  # never built -> no network, no cost


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


async def test_research_llm_fallback_maps_items() -> None:
    fake = _FakeExtractor(
        {LLMResearch: LLMResearch(
            name="Alan Turing",
            affiliation="University of Example",
            items=[
                LLMResearchItem(title="Computing Machinery and Intelligence",
                                url="https://x.com/paper", year=1950, venue="Mind"),
            ],
        )}
    )
    note = await ResearchParser().llm_fallback(_res(), fake)  # type: ignore[arg-type]
    assert isinstance(note, ResearchNote)
    assert note.items[0].year == 1950
    assert "[[Alan Turing]]" in note.body()


async def test_research_llm_fallback_no_items_returns_none() -> None:
    fake = _FakeExtractor({LLMResearch: LLMResearch(name="Alan Turing", items=[])})
    assert await ResearchParser().llm_fallback(_res(), fake) is None  # type: ignore[arg-type]


async def test_llm_fallback_returns_none_when_extractor_yields_nothing() -> None:
    fake = _FakeExtractor({})  # extract() returns None for every schema
    assert await ContactParser().llm_fallback(_res(), fake) is None  # type: ignore[arg-type]
