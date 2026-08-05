"""Tests for cross-platform filename sanitization + collision handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from webscraper_core.utils.sanitize import sanitize_filename, unique_path


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Hello World", "Hello World"),
        ("a/b:c?d*e", "a b c d e"),
        ('bad<>:"/\\|?*name', "bad name"),
        ("   spaced   out   ", "spaced out"),
        ("trailing dots...", "trailing dots"),
    ],
)
def test_illegal_chars_replaced(raw: str, expected: str) -> None:
    assert sanitize_filename(raw) == expected


def test_reserved_name_is_prefixed() -> None:
    assert sanitize_filename("CON").startswith("_")
    assert sanitize_filename("com1").startswith("_")


def test_truncation_to_max_length() -> None:
    stem = sanitize_filename("x" * 500)
    assert len(stem) <= 200


def test_empty_title_falls_back_to_hash_slug() -> None:
    stem = sanitize_filename("///", fallback_seed="https://example.com/team/jane")
    assert stem
    assert "example.com" in stem


def test_control_chars_removed() -> None:
    assert sanitize_filename("line\nbreak\ttab") == "line break tab"


def test_unique_path_no_collision(tmp_path: Path) -> None:
    p = unique_path(tmp_path, "note")
    assert p == tmp_path / "note.md"


def test_unique_path_increments_on_collision(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("x", encoding="utf-8")
    (tmp_path / "note (2).md").write_text("x", encoding="utf-8")
    assert unique_path(tmp_path, "note") == tmp_path / "note (3).md"
