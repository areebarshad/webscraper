"""Typer command-line interface.

Phase 1 ships the command surface; ``scrape`` is wired to the pipeline in Phase 2.
"""

from __future__ import annotations

import asyncio

import typer

from webscraper_core import __version__
from webscraper_core.pipeline import Pipeline, ScrapeError
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
    """Fetch, parse, and validate a single URL. (Vault export lands in Phase 3.)"""
    setup_logging()
    try:
        record = asyncio.run(Pipeline().run(url, task, force_dynamic=dynamic))
    except ScrapeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except (KeyError, NotImplementedError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    typer.secho(f"Parsed {record.note_kind}: {record.title()}", fg=typer.colors.GREEN)
    typer.echo("--- body preview ---")
    typer.echo(record.body())


if __name__ == "__main__":
    app()
