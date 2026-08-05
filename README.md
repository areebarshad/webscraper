# WebScraper → Obsidian

Modular, async Python web scraper that extracts unstructured web data (contacts,
news articles, public profiles) and writes clean Markdown — with YAML
frontmatter, tags, and `[[wikilinks]]` — straight into an Obsidian vault.

## Architecture

Tiered fetch/parse so cheap paths run first and expensive ones run only on
fallback:

```
URL(+task)
  -> fetcher router (httpx static  ->  Playwright dynamic on demand)
  -> parser (selectolax / bs4 / trafilatura, task-selected)
       -> llm_fallback (Claude structured output) when rules fail
  -> Pydantic validation
  -> Obsidian exporter (frontmatter + body + wikilinks, sanitized filename)
  -> vault/Articles|Contacts/<Title>.md
```

See `src/webscraper_core/` for the package and the phased plan for details.

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
cp .env.example .env    # add ANTHROPIC_API_KEY if using the LLM fallback
```

## Usage

```bash
uv run scraper version
uv run scraper scrape "https://example.com/article" --task article
uv run scraper scrape "https://example.com/team" --task contact
```

Configuration lives in `config.yaml`; override any value with `SCRAPER_`-prefixed
environment variables (`__` for nesting, e.g. `SCRAPER_FETCH__TIMEOUT=30`).

## Development

```bash
uv run pytest
uv run ruff check
uv run mypy src
```

## Status

Phase 1 (skeleton, config, ABCs, utilities) is in place. Static fetching,
parsers, the Obsidian exporter, dynamic Playwright fetching, and the Claude LLM
fallback land in Phases 2–5.
