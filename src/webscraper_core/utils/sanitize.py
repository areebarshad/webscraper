"""Cross-platform (Windows + POSIX) filename sanitization for vault notes."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import urlsplit

# Characters illegal on Windows (superset of POSIX restrictions) + control chars.
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WS = re.compile(r"\s+")

# Windows reserved device names (case-insensitive, with or without extension).
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

_MAX_STEM = 200  # keep filenames well under filesystem limits


def _short_hash(seed: str) -> str:
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]


def sanitize_filename(title: str, *, fallback_seed: str = "") -> str:
    """Return a safe filename stem (no extension) for ``title``.

    Replaces illegal chars, collapses whitespace, strips trailing dots/spaces,
    dodges reserved names, truncates, and falls back to a hash-based slug when
    the result would be empty.
    """
    stem = _ILLEGAL.sub(" ", title)
    stem = _WS.sub(" ", stem).strip()
    stem = stem.rstrip(" .")  # Windows forbids trailing dot/space

    if stem.upper().split(".")[0] in _RESERVED:
        stem = f"_{stem}"

    if len(stem) > _MAX_STEM:
        stem = stem[:_MAX_STEM].rstrip(" .")

    if not stem:
        seed = fallback_seed or title or "untitled"
        host = urlsplit(fallback_seed).netloc if "://" in fallback_seed else ""
        prefix = _WS.sub("-", host).strip("-") or "note"
        stem = f"{prefix}-{_short_hash(seed)}"

    return stem


def unique_path(directory: Path, stem: str, suffix: str = ".md") -> Path:
    """First non-colliding path in ``directory`` for ``stem``.

    Returns ``stem.md`` if free, else ``stem (2).md``, ``stem (3).md``, ...
    """
    candidate = directory / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    n = 2
    while True:
        candidate = directory / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1
