"""Obsidian exporter tests: rendering, frontmatter round-trip, paths, collisions."""

from __future__ import annotations

from pathlib import Path

import yaml

from webscraper_core.config import Settings
from webscraper_core.exporters.obsidian import ObsidianExporter, render_note
from webscraper_core.schemas.article import ArticleNote
from webscraper_core.schemas.contact import ContactNote


def _settings(tmp_path: Path, **kw: object) -> Settings:
    s = Settings(vault_path=tmp_path, **kw)  # type: ignore[arg-type]
    return s


def _article(title: str = "Hello World") -> ArticleNote:
    return ArticleNote(
        source_url="https://news.example.com/x",
        title_text=title,
        author="John Writer",
        content="Body text long enough to be a real article body." * 5,
    )


def _contact() -> ContactNote:
    return ContactNote(
        source_url="https://acme.com/team/jane",
        name="Jane Doe",
        emails=["jane@acme.com"],
        company="Acme Corp",
        socials={"linkedin": "https://linkedin.com/in/janedoe"},
    )


def _split_frontmatter(text: str) -> dict[str, object]:
    assert text.startswith("---\n")
    _, fm, _body = text.split("---\n", 2)
    return yaml.safe_load(fm)


def test_frontmatter_roundtrip_article() -> None:
    note = render_note(_article())
    fm = _split_frontmatter(note)
    assert fm["type"] == "article"
    assert fm["title"] == "Hello World"
    assert fm["author"] == "John Writer"
    assert "article" in fm["tags"]


def test_dangerous_title_does_not_break_yaml() -> None:
    note = render_note(_article(title='Weird: "quotes" and: colons'))
    fm = _split_frontmatter(note)
    assert fm["title"] == 'Weird: "quotes" and: colons'


def test_export_writes_article_to_articles_dir(tmp_path: Path) -> None:
    exporter = ObsidianExporter(_settings(tmp_path))
    path = exporter.export(_article())
    assert path == tmp_path / "Articles" / "Hello World.md"
    assert path.exists()
    fm = _split_frontmatter(path.read_text(encoding="utf-8"))
    assert fm["title"] == "Hello World"


def test_export_writes_contact_to_contacts_dir(tmp_path: Path) -> None:
    exporter = ObsidianExporter(_settings(tmp_path))
    path = exporter.export(_contact())
    assert path == tmp_path / "Contacts" / "Jane Doe.md"
    assert "[[Acme Corp]]" in path.read_text(encoding="utf-8")


def test_illegal_title_sanitized_in_path(tmp_path: Path) -> None:
    exporter = ObsidianExporter(_settings(tmp_path))
    path = exporter.export(_article(title="a/b:c?d"))
    assert path.name == "a b c d.md"


def test_collision_creates_unique_file(tmp_path: Path) -> None:
    exporter = ObsidianExporter(_settings(tmp_path))
    p1 = exporter.export(_article())
    p2 = exporter.export(_article())
    assert p1 != p2
    assert p2.name == "Hello World (2).md"


def test_overwrite_mode_reuses_path(tmp_path: Path) -> None:
    exporter = ObsidianExporter(_settings(tmp_path, overwrite_existing=True))
    p1 = exporter.export(_article())
    p2 = exporter.export(_article())
    assert p1 == p2
