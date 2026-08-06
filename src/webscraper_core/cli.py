"""Typer command-line interface.

Phase 1 ships the command surface; ``scrape`` is wired to the pipeline in Phase 2.
"""

from __future__ import annotations

import asyncio

import httpx
import typer

from webscraper_core import __version__
from webscraper_core.pipeline import Pipeline, ScrapeError
from webscraper_core.utils.logging import setup_logging
from webscraper_core.utils.retry import RetryableStatus

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
    write: bool = typer.Option(
        True, "--write/--no-write", help="Write the note to the vault, or preview only."
    ),
) -> None:
    """Fetch, parse, validate, and write a single URL into the Obsidian vault."""
    setup_logging()
    pipeline = Pipeline()
    try:
        if write:
            path = asyncio.run(pipeline.scrape_to_vault(url, task, force_dynamic=dynamic))
            typer.secho(f"Wrote {path}", fg=typer.colors.GREEN)
        else:
            record = asyncio.run(pipeline.run(url, task, force_dynamic=dynamic))
            typer.secho(f"Parsed {record.note_kind}: {record.title()}", fg=typer.colors.GREEN)
            typer.echo("--- note preview ---")
            from webscraper_core.exporters.obsidian import render_note

            typer.echo(render_note(record))
    except ScrapeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except (httpx.HTTPError, RetryableStatus) as exc:
        typer.secho(f"fetch failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except (KeyError, NotImplementedError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc


if __name__ == "__main__":
    app()
