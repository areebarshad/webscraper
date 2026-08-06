"""Typer command-line interface for the scraper."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import typer

from webscraper_core import __version__
from webscraper_core.config import Settings, load_settings
from webscraper_core.crawler import Crawler
from webscraper_core.exporters.index import build_index
from webscraper_core.parsers.registry import available_tasks
from webscraper_core.pipeline import Pipeline, ScrapeError
from webscraper_core.utils.logging import setup_logging
from webscraper_core.utils.retry import RetryableStatus

app = typer.Typer(
    add_completion=False,
    help="Scrape web pages into an Obsidian vault as clean Markdown notes.",
)

# Errors that mean "this URL couldn't be scraped" rather than a bug.
_FETCH_ERRORS = (ScrapeError, httpx.HTTPError, RetryableStatus)


def _make_settings(vault: Path | None, overwrite: bool = False) -> Settings:
    settings = load_settings()
    if vault is not None:
        settings.vault_path = vault
    if overwrite:
        settings.overwrite_existing = True
    return settings


def _pipeline(vault: Path | None, overwrite: bool = False) -> Pipeline:
    return Pipeline(_make_settings(vault, overwrite))


def _maybe_index(pipeline: Pipeline, override: bool | None) -> None:
    """Rebuild Index.md if requested, or per the vault's auto_index setting."""
    do = pipeline.settings.auto_index if override is None else override
    if do:
        build_index(pipeline.settings)


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(__version__)


@app.command()
def tasks() -> None:
    """List the available scrape tasks."""
    for name in available_tasks():
        typer.echo(name)


@app.command()
def index(
    vault: Path | None = typer.Option(None, "--vault", help="Override the vault path."),
) -> None:
    """(Re)build the vault Index.md linking every scraped note."""
    setup_logging()
    path = build_index(_make_settings(vault))
    typer.secho(f"Wrote {path}", fg=typer.colors.GREEN)


@app.command()
def scrape(
    url: str = typer.Argument(..., help="URL to scrape."),
    task: str = typer.Option(..., "--task", "-t", help=f"One of: {', '.join(available_tasks())}."),
    dynamic: bool = typer.Option(False, "--dynamic", help="Force the Playwright fetcher."),
    write: bool = typer.Option(
        True, "--write/--no-write", help="Write the note to the vault, or preview only."
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite an existing note."),
    rebuild_index: bool | None = typer.Option(
        None, "--index/--no-index", help="Rebuild Index.md afterwards (default: config)."
    ),
    vault: Path | None = typer.Option(None, "--vault", help="Override the vault path."),
) -> None:
    """Fetch, parse, validate, and write a single URL into the Obsidian vault."""
    setup_logging()
    pipeline = _pipeline(vault, overwrite)
    try:
        if write:
            path = asyncio.run(pipeline.scrape_to_vault(url, task, force_dynamic=dynamic))
            typer.secho(f"Wrote {path}", fg=typer.colors.GREEN)
            _maybe_index(pipeline, rebuild_index)
        else:
            record = asyncio.run(pipeline.run(url, task, force_dynamic=dynamic))
            typer.secho(f"Parsed {record.note_kind}: {record.title()}", fg=typer.colors.GREEN)
            typer.echo("--- note preview ---")
            from webscraper_core.exporters.obsidian import render_note

            typer.echo(render_note(record))
    except _FETCH_ERRORS as exc:
        typer.secho(f"could not scrape: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except (KeyError, NotImplementedError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc


@app.command()
def person(
    url: str = typer.Argument(..., help="A person/faculty page URL."),
    dynamic: bool = typer.Option(False, "--dynamic", help="Force the Playwright fetcher."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing notes."),
    rebuild_index: bool | None = typer.Option(
        None, "--index/--no-index", help="Rebuild Index.md afterwards (default: config)."
    ),
    vault: Path | None = typer.Option(None, "--vault", help="Override the vault path."),
) -> None:
    """Scrape a person once into both a contact note and a research note.

    Contact info lands in Contacts/, publications in Research/, cross-linked by
    the person's name (a [[Name]] wikilink resolves between the two).
    """
    setup_logging()
    pipeline = _pipeline(vault, overwrite)
    any_ok = False
    for task in ("contact", "research"):
        try:
            path = asyncio.run(pipeline.scrape_to_vault(url, task, force_dynamic=dynamic))
            typer.secho(f"Wrote {task}: {path}", fg=typer.colors.GREEN)
            any_ok = True
        except _FETCH_ERRORS as exc:
            typer.secho(f"no {task} note: {exc}", fg=typer.colors.YELLOW, err=True)
    if not any_ok:
        typer.secho("Nothing extracted for this person.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    _maybe_index(pipeline, rebuild_index)


@app.command()
def batch(
    urls: list[str] = typer.Argument(None, help="URLs to scrape (or use --file)."),
    task: str = typer.Option(..., "--task", "-t", help=f"One of: {', '.join(available_tasks())}."),
    file: Path | None = typer.Option(None, "--file", help="File with one URL per line."),
    concurrency: int = typer.Option(5, "--concurrency", "-c", help="Max concurrent fetches."),
    dynamic: bool = typer.Option(False, "--dynamic", help="Force the Playwright fetcher."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing notes."),
    rebuild_index: bool | None = typer.Option(
        None, "--index/--no-index", help="Rebuild Index.md afterwards (default: config)."
    ),
    vault: Path | None = typer.Option(None, "--vault", help="Override the vault path."),
) -> None:
    """Scrape many URLs of the same task, writing a note for each success."""
    setup_logging()
    all_urls = list(urls or [])
    if file is not None:
        lines = file.read_text(encoding="utf-8").splitlines()
        all_urls += [ln.strip() for ln in lines if ln.strip()]
    if not all_urls:
        typer.secho("No URLs given (pass URLs or --file).", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)

    pipeline = _pipeline(vault, overwrite)
    results = asyncio.run(
        pipeline.run_many(all_urls, task, concurrency=concurrency, force_dynamic=dynamic)
    )
    ok = 0
    for url, result in zip(all_urls, results, strict=True):
        if isinstance(result, Exception):
            typer.secho(f"  ✗ {url}: {result}", fg=typer.colors.YELLOW)
            continue
        path = pipeline.exporter.export(result)
        typer.secho(f"  ✓ {url} → {path.name}", fg=typer.colors.GREEN)
        ok += 1
    typer.secho(f"Done: {ok}/{len(all_urls)} written.", fg=typer.colors.CYAN)
    if ok:
        _maybe_index(pipeline, rebuild_index)
    if ok == 0:
        raise typer.Exit(code=1)


@app.command()
def crawl(
    url: str = typer.Argument(..., help="Seed URL to crawl from (a hub/list/directory page)."),
    task: str = typer.Option(
        "auto",
        "--task",
        "-t",
        help="Child task type, or 'auto' to infer per page (see `scraper tasks`).",
    ),
    depth: int | None = typer.Option(
        None, "--depth", help="Levels of sub-links to follow (default: config, 1)."
    ),
    max_pages: int | None = typer.Option(
        None, "--max-pages", help="Safety cap on pages scraped (default: config, 20)."
    ),
    same_domain: bool | None = typer.Option(
        None,
        "--same-domain/--allow-external",
        help="Stay on the seed host, or follow links to other domains.",
    ),
    concurrency: int = typer.Option(5, "--concurrency", "-c", help="Max concurrent fetches."),
    dynamic: bool = typer.Option(False, "--dynamic", help="Force the Playwright fetcher."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing notes."),
    rebuild_index: bool | None = typer.Option(
        None, "--index/--no-index", help="Rebuild Index.md afterwards (default: config)."
    ),
    vault: Path | None = typer.Option(None, "--vault", help="Override the vault path."),
) -> None:
    """Recursively crawl a seed page into a hub note plus linked child notes."""
    setup_logging()
    if task != "auto" and task not in available_tasks():
        typer.secho(
            f"unknown task {task!r}; use 'auto' or one of: {', '.join(available_tasks())}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=2)

    pipeline = _pipeline(vault, overwrite)
    cfg = pipeline.settings.crawl
    crawler = Crawler(pipeline)
    try:
        summary = asyncio.run(
            crawler.crawl(
                url,
                task=task,
                depth=cfg.default_depth if depth is None else depth,
                max_pages=cfg.max_pages if max_pages is None else max_pages,
                same_domain=cfg.same_domain if same_domain is None else same_domain,
                force_dynamic=dynamic,
                concurrency=concurrency,
            )
        )
    except _FETCH_ERRORS as exc:
        typer.secho(f"could not crawl seed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    for child_url, reason in summary.failures:
        typer.secho(f"  ✗ {child_url}: {reason}", fg=typer.colors.YELLOW)
    for path in summary.child_paths:
        typer.secho(f"  ✓ {path.name}", fg=typer.colors.GREEN)
    if summary.hub_path is not None:
        typer.secho(f"Hub: {summary.hub_path}", fg=typer.colors.CYAN)
    typer.secho(
        f"Done: {len(summary.child_paths)} child note(s) under '{summary.hub_title}'.",
        fg=typer.colors.CYAN,
    )
    _maybe_index(pipeline, rebuild_index)
    if summary.written == 0:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
