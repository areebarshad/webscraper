"""Obsidian exporter tests: rendering, frontmatter round-trip, paths, collisions."""

from __future__ import annotations

from pathlib import Path

import yaml

from webscraper_core.config import Settings
from webscraper_core.exporters.obsidian import ObsidianExporter, render_note
from webscraper_core.schemas.contact import ContactNote
from webscraper_core.schemas.profile import ProfileNote
from webscraper_core.schemas.research import ResearchItem, ResearchNote


def _settings(tmp_path: Path, **kw: object) -> Settings:
    s = Settings(vault_path=tmp_path, **kw)  # type: ignore[arg-type]
    return s


def _profile(title: str = "Hello World") -> ProfileNote:
    return ProfileNote(
        source_url="https://devhub.io/x",
        name=title,
        headline="Engineer",
        bio="Builds things.",
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


def test_frontmatter_roundtrip_profile() -> None:
    note = render_note(_profile())
    fm = _split_frontmatter(note)
    assert fm["type"] == "profile"
    assert fm["name"] == "Hello World"
    assert fm["headline"] == "Engineer"
    assert "profile" in fm["tags"]


def test_dangerous_title_does_not_break_yaml() -> None:
    note = render_note(_profile(title='Weird: "quotes" and: colons'))
    fm = _split_frontmatter(note)
    assert fm["name"] == 'Weird: "quotes" and: colons'


def test_export_writes_profile_to_profiles_dir(tmp_path: Path) -> None:
    exporter = ObsidianExporter(_settings(tmp_path))
    path = exporter.export(_profile())
    assert path == tmp_path / "Profiles" / "Hello World.md"
    assert path.exists()
    fm = _split_frontmatter(path.read_text(encoding="utf-8"))
    assert fm["name"] == "Hello World"


def test_export_writes_contact_to_contacts_dir(tmp_path: Path) -> None:
    exporter = ObsidianExporter(_settings(tmp_path))
    path = exporter.export(_contact())
    assert path == tmp_path / "Contacts" / "Jane Doe.md"
    assert "[[Acme Corp]]" in path.read_text(encoding="utf-8")


def test_export_writes_research_to_research_dir(tmp_path: Path) -> None:
    note = ResearchNote(
        source_url="https://example.edu/~turing",
        name="Alan Turing",
        items=[ResearchItem(title="Computing Machinery and Intelligence", year=1950)],
    )
    path = ObsidianExporter(_settings(tmp_path)).export(note)
    assert path == tmp_path / "Research" / "Alan Turing - Research.md"
    assert "[[Alan Turing]]" in path.read_text(encoding="utf-8")


def test_illegal_title_sanitized_in_path(tmp_path: Path) -> None:
    exporter = ObsidianExporter(_settings(tmp_path))
    path = exporter.export(_profile(title="a/b:c?d"))
    assert path.name == "a b c d.md"


def test_collision_creates_unique_file(tmp_path: Path) -> None:
    exporter = ObsidianExporter(_settings(tmp_path))
    p1 = exporter.export(_profile())
    p2 = exporter.export(_profile())
    assert p1 != p2
    assert p2.name == "Hello World (2).md"


def test_overwrite_mode_reuses_path(tmp_path: Path) -> None:
    exporter = ObsidianExporter(_settings(tmp_path, overwrite_existing=True))
    p1 = exporter.export(_profile())
    p2 = exporter.export(_profile())
    assert p1 == p2
