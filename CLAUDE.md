# CLAUDE.md

Guidance for AI agents (and humans) working in this repository. Read this before
changing scraping, parsing, or export behavior.

## What this project is

An async Python web scraper that extracts unstructured web data and writes clean
Markdown notes into an Obsidian vault. It uses a **tiered pipeline** so cheap
paths run first and expensive ones run only on fallback:

```
URL (+ task)
  → fetch      httpx (static)  →  Playwright (dynamic, on demand)
  → parse      selectolax / bs4 / trafilatura, chosen per task
       ↳ llm_fallback (Claude structured output) only if rules fail
  → validate   Pydantic v2 — the exporter never sees a malformed record
  → export     Obsidian note (YAML frontmatter + body + [[wikilinks]])
  → vault/<Category>/<Title>.md
```

## Golden rules — do not break these

1. **Validation is the contract.** Every record is a Pydantic `ScrapeRecord`
   subclass. If a parser can't extract confidently, it returns `None` (never a
   half-filled record). The exporter only ever receives validated records.
2. **The exporter owns the vault, and only the vault.** Notes are written under
   `vault/<Category>/`. Filenames go through `utils/sanitize.py` — never build a
   path by hand. Frontmatter is emitted via `yaml.safe_dump`, never string
   concatenation, so titles with `:`, quotes, or newlines can't corrupt a note.
3. **Fallbacks must never crash the run.** `llm_fallback` and dynamic-fetch
   escalation catch their own failures and return `None` / skip. A single bad
   URL must not abort a batch.
4. **The LLM is opt-in and cost-guarded.** `LLMExtractor` does nothing unless
   `SCRAPER_LLM__ENABLED=true` and `ANTHROPIC_API_KEY` is set. Don't call the
   Anthropic API in tests — use a fake extractor (see `tests/test_llm.py`).
5. **Git is the user's job.** Never run `git commit`/`push`/`merge`/`rebase`.
   Suggest the commands; the user runs them.

## Layout

```
src/webscraper_core/
  cli.py          Typer CLI: scrape, person, batch, tasks, version
  config.py       pydantic-settings (config.yaml + SCRAPER_ env overrides)
  pipeline.py     orchestrator: fetch → parse → llm_fallback → validate → export
  fetchers/       base, static (httpx), dynamic (Playwright), router
  parsers/        base (+ llm_fallback hook), article, contact, profile,
                  research, registry
  schemas/        base, article, contact, profile, research, llm
  exporters/      base, obsidian (frontmatter + body + sanitize + collisions)
  llm/            anthropic_client (Claude structured-output extractor)
  utils/          throttle, retry, useragent, sanitize, logging
```

## Categories → vault folders

| Task       | Note type | Folder        | Holds |
|------------|-----------|---------------|-------|
| `article`  | article   | `Articles/`   | News/articles: title, author, date, clean body |
| `contact`  | contact   | `Contacts/`   | A person's contact info: emails, phones, company, socials |
| `profile`  | profile   | `Profiles/`   | A public profile: name, headline, bio, location |
| `research` | research  | `Research/`   | A person's publications, each with a source link |

**The person workflow.** `scraper person <url>` scrapes one page into both a
`contact` note and a `research` note. Scraping "Professor X" puts their contact
details in `Contacts/Professor X.md` and their publications in
`Research/Professor X - Research.md`; the research note links back with a
`[[Professor X]]` wikilink so the two resolve to each other in Obsidian's graph.

## Adding a new task (the extension pattern)

1. `schemas/<task>.py` — a `ScrapeRecord` subclass with `note_kind`, `title()`,
   `frontmatter()`, `body()`. Reject empty/uninformative records in validators.
2. `parsers/<task>.py` — a `BaseParser` subclass; set `task` and `engine`,
   implement `parse()`, and optionally `async llm_fallback()` (add an
   `schemas/llm.py` schema for it).
3. Register the parser in `parsers/registry.py`.
4. Map `note_kind` → a folder in `exporters/obsidian.py` and add a
   `<task>_dir` field in `config.py` + `config.yaml`.
5. Add a fixture in `tests/fixtures/` and tests (parser offline + llm fallback
   with a fake extractor + exporter routing).

Fetchers, exporter, and utils don't change.

## Running & checking

```bash
uv sync --extra dev                        # base + dev tools
uv sync --extra dev --extra dynamic        # + Playwright, then:
uv run playwright install chromium

uv run pytest            # all tests are offline (fixtures + fakes) — no network
uv run ruff check
uv run mypy src

uv run scraper tasks
uv run scraper scrape "<url>" --task article --no-write   # preview, no write
uv run scraper person "<faculty-url>"                     # contact + research
uv run scraper batch "<url1>" "<url2>" --task contact     # or --file urls.txt
```

Use `--vault <path>` (or `SCRAPER_VAULT_PATH`) to write somewhere other than
`vault/` — always do this in tests/experiments so you don't touch the real vault.

## Conventions

- Python 3.11+, async throughout. Reuse one `httpx.AsyncClient` per run.
- Be a polite scraper: the per-host token-bucket throttle, UA rotation, and
  exponential-backoff retry in `utils/` are wired into fetchers — keep them there.
- Model choice for the LLM fallback lives in `config.yaml` (`llm.model`); default
  is a current Claude model. Use `client.messages.parse(output_format=...)` for
  structured extraction — never hand-roll JSON parsing.
