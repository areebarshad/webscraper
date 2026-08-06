"""Offline parser tests against saved HTML fixtures (no network)."""

from __future__ import annotations

from webscraper_core.fetchers.base import FetchResult
from webscraper_core.parsers.article import ArticleParser
from webscraper_core.parsers.contact import ContactParser
from webscraper_core.parsers.profile import ProfileParser
from webscraper_core.parsers.registry import available_tasks, get_parser
from webscraper_core.parsers.research import ResearchParser


def test_registry_tasks() -> None:
    assert available_tasks() == ["article", "contact", "profile", "research"]
    assert isinstance(get_parser("article"), ArticleParser)


def test_registry_unknown_task() -> None:
    try:
        get_parser("nope")
    except KeyError as exc:
        assert "nope" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected KeyError")


def test_article_parse(article_result: FetchResult) -> None:
    note = ArticleParser().parse(article_result)
    assert note is not None
    assert "Bakery" in note.title_text
    assert note.author == "John Writer"
    assert note.published is not None and note.published.year == 2026
    assert note.site == "news.example.com"
    assert len(note.content) > 200
    assert "[[John Writer]]" in note.body()


def test_article_parse_empty_returns_none(empty_result: FetchResult) -> None:
    assert ArticleParser().parse(empty_result) is None


def test_contact_parse(contact_result: FetchResult) -> None:
    note = ContactParser().parse(contact_result)
    assert note is not None
    assert note.name == "Jane Doe"
    assert "jane.doe@acme.com" in note.emails
    assert any("555" in p for p in note.phones)
    assert note.socials.get("linkedin", "").endswith("/janedoe")
    assert note.socials.get("twitter")  # x.com/twitter.com mapped
    assert note.company == "Acme Corp"
    assert "[[Acme Corp]]" in note.body()


def test_contact_parse_empty_returns_none(empty_result: FetchResult) -> None:
    assert ContactParser().parse(empty_result) is None


def test_profile_parse(profile_result: FetchResult) -> None:
    note = ProfileParser().parse(profile_result)
    assert note is not None
    assert note.name == "Jane Doe"
    assert note.headline and "Engineering" in note.headline
    assert note.location == "Berlin, Germany"
    assert note.socials.get("github", "").endswith("/janedoe")
    assert "jane@devhub.io" in note.emails
    assert note.note_kind == "profile"


def test_profile_parse_empty_returns_none(empty_result: FetchResult) -> None:
    assert ProfileParser().parse(empty_result) is None


def test_research_parse(research_result: FetchResult) -> None:
    note = ResearchParser().parse(research_result)
    assert note is not None
    assert "Turing" in note.name
    assert len(note.items) >= 3
    # The two linked papers keep absolute URLs; years are pulled from the text.
    urls = [i.url for i in note.items if i.url]
    assert any(u.startswith("https://example.edu") for u in urls)
    assert any(i.year == 1950 for i in note.items)
    body = note.body()
    assert "[[Prof. Alan Turing]]" in body  # links back to the contact note


def test_research_parse_empty_returns_none(empty_result: FetchResult) -> None:
    assert ResearchParser().parse(empty_result) is None
