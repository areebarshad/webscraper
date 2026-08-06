"""Offline parser tests against saved HTML fixtures (no network)."""

from __future__ import annotations

from webscraper_core.fetchers.base import FetchResult
from webscraper_core.parsers.article import ArticleParser
from webscraper_core.parsers.contact import ContactParser
from webscraper_core.parsers.registry import available_tasks, get_parser


def test_registry_tasks() -> None:
    assert available_tasks() == ["article", "contact"]
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
