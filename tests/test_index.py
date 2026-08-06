"""Vault index (map-of-content) builder tests."""

from __future__ import annotations

from pathlib import Path

import yaml

from webscraper_core.config import Settings
from webscraper_core.exporters.index import build_index


def _settings(tmp_path: Path) -> Settings:
    return Settings(vault_path=tmp_path)


def _split_frontmatter(text: str) -> dict[str, object]:
    _, fm, _body = text.split("---\n", 2)
    return yaml.safe_load(fm)


def test_index_lists_notes_by_category(tmp_path: Path) -> None:
    (tmp_path / "Articles").mkdir()
    (tmp_path / "Articles" / "Some Story.md").write_text("x", encoding="utf-8")
    (tmp_path / "Research").mkdir()
    (tmp_path / "Research" / "Alan Turing - Research.md").write_text("x", encoding="utf-8")

    path = build_index(_settings(tmp_path))
    assert path == tmp_path / "Index.md"
    text = path.read_text(encoding="utf-8")

    fm = _split_frontmatter(text)
    assert fm["type"] == "index"
    assert fm["note_count"] == 2
    assert "## Articles (1)" in text
    assert "[[Some Story]]" in text
    assert "[[Alan Turing - Research]]" in text


def test_index_on_empty_vault(tmp_path: Path) -> None:
    path = build_index(_settings(tmp_path))
    assert path.exists()
    assert "No notes yet" in path.read_text(encoding="utf-8")


def test_index_excludes_itself(tmp_path: Path) -> None:
    (tmp_path / "Articles").mkdir()
    (tmp_path / "Articles" / "A.md").write_text("x", encoding="utf-8")
    build_index(_settings(tmp_path))
    # A second build must not list the Index.md it just wrote at vault root.
    text = build_index(_settings(tmp_path)).read_text(encoding="utf-8")
    assert "[[Index]]" not in text
