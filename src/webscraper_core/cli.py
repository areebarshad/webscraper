"""Typer command-line interface.

Phase 1 ships the command surface; ``scrape`` is wired to the pipeline in Phase 2.
"""

from __future__ import annotations

import typer

from webscraper_core import __version__
from webscraper_core.config import load_settings
from webscraper_core.utils.logging import setup_logging

app = typer.Typer(
    add_completion=False,
    help="Scrape web pages into an Obsidian vault as clean Markdown notes.",
)


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(__version__)


@app.command()
def scrape(
    url: str = typer.Argument(..., help="URL to scrape."),
    task: str = typer.Option(..., "--task", "-t", help="Parser task, e.g. article|contact."),
    dynamic: bool = typer.Option(
        False, "--dynamic", help="Force the Playwright fetcher (Phase 4)."
    ),
) -> None:
    """Fetch, parse, and export a single URL. (Pipeline wiring lands in Phase 2.)"""
    setup_logging()
    settings = load_settings()
    typer.echo(
        f"[stub] would scrape task={task!r} dynamic={dynamic} url={url}\n"
        f"       vault={settings.vault_path}  (pipeline arrives in Phase 2)"
    )
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
