"""Build a vault index (map-of-content) note linking every scraped note.

Writes ``vault/Index.md`` with one section per category, each listing its notes
as ``[[wikilinks]]`` — a single hub you can open in Obsidian to reach everything.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from webscraper_core.config import Settings
from webscraper_core.exporters.obsidian import render_frontmatter
from webscraper_core.utils.logging import get_logger

log = get_logger(__name__)

INDEX_FILENAME = "Index.md"


def build_index(settings: Settings) -> Path:
    """(Re)generate the vault index note and return its path."""
    vault = settings.vault_path
    categories = [
        ("Articles", settings.articles_dir),
        ("Contacts", settings.contacts_dir),
        ("Profiles", settings.profiles_dir),
        ("Research", settings.research_dir),
    ]

    sections: list[str] = []
    total = 0
    for label, subdir in categories:
        directory = vault / subdir
        if not directory.exists():
            continue
        stems = sorted(
            p.stem for p in directory.glob("*.md") if p.name != INDEX_FILENAME
        )
        if not stems:
            continue
        total += len(stems)
        lines = [f"## {label} ({len(stems)})", ""]
        lines += [f"- [[{stem}]]" for stem in stems]
        sections.append("\n".join(lines))

    frontmatter = render_frontmatter(
        {
            "type": "index",
            "generated_at": datetime.now(UTC).replace(microsecond=0),
            "note_count": total,
            "tags": ["index", "moc", "scraped"],
        }
    )
    body = "# Vault Index\n\n"
    body += "\n\n".join(sections) if sections else "_No notes yet._\n"

    vault.mkdir(parents=True, exist_ok=True)
    path = vault / INDEX_FILENAME
    path.write_text(frontmatter + "\n" + body.rstrip() + "\n", encoding="utf-8")
    log.info("wrote vault index (%d notes) -> %s", total, path)
    return path
