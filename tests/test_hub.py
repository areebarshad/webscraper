"""Hub note + crawler parent-linkage rendering tests."""

from __future__ import annotations

from webscraper_core.exporters.obsidian import render_note
from webscraper_core.schemas.contact import ContactNote
from webscraper_core.schemas.hub import HubNote


def test_hub_lists_children_as_wikilinks() -> None:
    hub = HubNote(
        source_url="https://dept.edu/faculty",
        title_text="Physics Faculty",
        children=["Alice Smith", "Bob Jones"],
    )
    body = hub.body()
    assert "## Contents (2)" in body
    assert "- [[Alice Smith]]" in body
    assert "- [[Bob Jones]]" in body


def test_empty_hub_still_renders() -> None:
    hub = HubNote(source_url="https://x.edu", title_text="Empty Hub")
    body = hub.body()
    assert "## Contents (0)" in body
    assert "No child notes" in body


def test_parent_wired_into_frontmatter_and_backlink() -> None:
    note = ContactNote(
        source_url="https://dept.edu/faculty/alice",
        name="Alice Smith",
        emails=["alice@dept.edu"],
        parent="Physics Faculty",
    )
    rendered = render_note(note)
    assert "parent:" in rendered  # frontmatter key
    assert "[[Physics Faculty]]" in rendered
    assert "> Part of [[Physics Faculty]]" in rendered


def test_parent_absent_leaves_note_unchanged() -> None:
    note = ContactNote(
        source_url="https://dept.edu/faculty/alice",
        name="Alice Smith",
        emails=["alice@dept.edu"],
    )
    rendered = render_note(note)
    assert "parent:" not in rendered
    assert "Part of" not in rendered
