"""Graph-connection tests: reciprocal person links, hubs, and auto-index logic."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from webscraper_core import cli
from webscraper_core.config import Settings
from webscraper_core.schemas.contact import ContactNote
from webscraper_core.schemas.research import ResearchItem, ResearchNote


def _contact() -> ContactNote:
    return ContactNote(
        source_url="https://acme.com/jane",
        name="Jane Doe",
        emails=["jane@acme.com"],
        company="Acme Corp",
    )


def _research(affiliation: str) -> ResearchNote:
    return ResearchNote(
        source_url="https://x.edu/jane",
        name="Jane Doe",
        affiliation=affiliation,
        items=[ResearchItem(title="A Paper", year=2020)],
    )


def test_contact_links_to_company_hub() -> None:
    assert "[[Acme Corp]]" in _contact().body()  # company hub


def test_research_links_back_to_contact() -> None:
    # The one edge that connects the person's research and contact notes in the graph.
    assert "[[Jane Doe]]" in _research("University of Example").body()


def test_research_affiliation_org_is_a_hub() -> None:
    assert "[[University of Example]]" in _research("University of Example").body()


def test_research_affiliation_dotted_abbreviation_is_a_hub() -> None:
    assert "[[N.Y.U.]]" in _research("N.Y.U.").body()  # not mistaken for a domain


def test_research_affiliation_bare_domain_stays_plain() -> None:
    body = _research("en.wikipedia.org").body()
    assert "en.wikipedia.org" in body
    assert "[[en.wikipedia.org]]" not in body  # no giant domain hub node


def test_auto_index_default_on() -> None:
    assert Settings().auto_index is True


@pytest.mark.parametrize(
    "auto, override, expected",
    [(True, None, True), (False, None, False), (False, True, True), (True, False, False)],
)
def test_maybe_index_decision(
    monkeypatch: pytest.MonkeyPatch, auto: bool, override: bool | None, expected: bool
) -> None:
    calls: list[object] = []
    monkeypatch.setattr(cli, "build_index", lambda settings: calls.append(settings))
    pipeline = SimpleNamespace(settings=SimpleNamespace(auto_index=auto))
    cli._maybe_index(pipeline, override)  # type: ignore[arg-type]
    assert bool(calls) is expected
