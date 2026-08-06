"""Offline parser tests against saved HTML fixtures (no network)."""

from __future__ import annotations

from webscraper_core.fetchers.base import FetchResult
from webscraper_core.parsers.contact import ContactParser
from webscraper_core.parsers.profile import ProfileParser
from webscraper_core.parsers.registry import available_tasks, get_parser
from webscraper_core.parsers.research import ResearchParser


def test_registry_tasks() -> None:
    assert available_tasks() == ["contact", "profile", "research"]
    assert isinstance(get_parser("contact"), ContactParser)


def test_registry_unknown_task() -> None:
    try:
        get_parser("nope")
    except KeyError as exc:
        assert "nope" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected KeyError")


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


_JSONLD_CONTACT = """
<html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"Person","name":"Dr. Grace Hopper",
 "email":"grace@navy.mil","telephone":"+1-202-555-0143",
 "worksFor":{"@type":"Organization","name":"US Navy"}}
</script></head><body>
  <h1>Faculty</h1>
  <p>Reach the office at <a href="tel:+12025550188">+1 202 555 0188</a>.</p>
  <footer>Call our spam line +1 000 000 0000</footer>
</body></html>
"""


def test_contact_company_from_domain() -> None:
    html = "<html><body><h1>Jane</h1><a href='mailto:j@x.com'>e</a></body></html>"

    def company_for(url: str) -> str | None:
        res = FetchResult(url=url, final_url=url, status=200, html=html)
        note = ContactParser().parse(res)
        return note.company if note else None

    assert company_for("https://en.wikipedia.org/x") == "Wikipedia"  # skip subdomain
    assert company_for("https://example.co.uk/x") == "Example"       # skip .co.uk suffix
    assert company_for("https://acme.com/x") == "Acme"


def test_contact_uses_jsonld_and_tel() -> None:
    res = FetchResult(url="https://navy.mil/g", final_url="https://navy.mil/g",
                      status=200, html=_JSONLD_CONTACT)
    note = ContactParser().parse(res)
    assert note is not None
    assert note.name == "Dr. Grace Hopper"        # from JSON-LD, not the <h1>
    assert "grace@navy.mil" in note.emails         # JSON-LD email
    assert note.company == "US Navy"               # JSON-LD worksFor
    assert any("0143" in p for p in note.phones)   # JSON-LD telephone
    assert any("0188" in p for p in note.phones)   # tel: link
    # Footer number is stripped as noise, so it must not appear.
    assert not any("000 000 0000" in p for p in note.phones)


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
