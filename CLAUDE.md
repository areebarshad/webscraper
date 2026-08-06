# CLAUDE.md

Guidance for AI agents (and humans) working in this repository. Read this before
changing scraping, parsing, or export behavior.

## What this project is

An async Python web scraper that extracts unstructured web data and writes clean
Markdown notes into an Obsidian vault. It uses a **tiered pipeline** so cheap
paths run first and expensive ones run only on fallback:

```
URL (+ task)
  → robots     RobotsGate — skip if the site's robots.txt disallows the path
  → fetch      httpx (static)  →  Playwright (dynamic, on demand)
  → parse      selectolax / bs4 / trafilatura, chosen per task
       ↳ llm_fallback (Claude structured output) only if rules fail
  → validate   Pydantic v2 — the exporter never sees a malformed record
  → export     Obsidian note (YAML frontmatter + body + [[wikilinks]])
  → vault/<Category>/<Title>.md
```

`exporters/index.py` builds a separate `vault/Index.md` map-of-content linking
every note by category. It's rebuilt automatically after each scrape command
(config `auto_index`, default on; override per-run with `--index/--no-index`) or
on demand via `scraper index`.

**Graph connections** are deliberate — keep notes cross-linked:
- A research note links to its person's contact with `[[Name]]` (the edge that
  ties a person's research and contact notes together in the graph). Don't add a
  reciprocal `[[Name - Research]]` from the contact side — it dangles as a junk
  node for non-person / research-less contacts.
- Contact/profile/research link their company/affiliation as `[[Org]]` (a shared
  hub) — but a bare domain affiliation is left plain to avoid a junk hub node.
- Articles link `[[Author]]`. When adding a note type, wire it into an existing
  hub (person, org, or author) rather than leaving it an island.

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
4. **The LLM is opt-in, cost-guarded, and last.** `LLMExtractor` does nothing
   unless `SCRAPER_LLM__ENABLED=true` and `ANTHROPIC_API_KEY` is set. It runs only
   after rule parsers return `None`, is sent **cleaned** page text (never raw
   HTML — `readable_text` uses trafilatura / `utils/htmlclean.clean_text`), and is
   **skipped entirely** when that text is shorter than `llm.min_chars` (404s /
   empty JS shells). Keep it this way: improve the rule parsers before reaching
   for the model. Don't call the Anthropic API in tests — use a fake extractor.
5. **Git is the user's job.** Never run `git commit`/`push`/`merge`/`rebase`.
   Suggest the commands; the user runs them.
6. **Stay a polite crawler.** `RobotsGate` (checked in `pipeline.run`) honors
   `robots.txt` by default. Don't remove or bypass it; it's disabled only via
   `SCRAPER_FETCH__RESPECT_ROBOTS=false`. Robots results are cached per host.

## Layout

```
src/webscraper_core/
  cli.py          Typer CLI: scrape, person, batch, index, tasks, version
  config.py       pydantic-settings (config.yaml + SCRAPER_ env overrides)
  pipeline.py     orchestrator: robots → fetch → parse → llm_fallback → validate → export
  fetchers/       base, static (httpx), dynamic (Playwright), router
  parsers/        base (+ llm_fallback hook), article, contact, profile,
                  research, registry
  schemas/        base, article, contact, profile, research, llm
  exporters/      base, obsidian (note writing), index (vault map-of-content)
  llm/            anthropic_client (Claude structured-output extractor)
  utils/          throttle, retry, useragent, sanitize, robots, htmlclean, logging
```

`utils/htmlclean.py` is the shared cleaner: `strip_noise` / `clean_text` drop
scripts, nav, footers, and forms; `mailto_addresses` / `tel_numbers` /
`find_jsonld` let rule parsers read links and schema.org data natively. Prefer
these over scanning raw HTML — they cut false positives in the parsers and LLM
input tokens by ~80–90%.

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
uv run scraper index                                      # (re)build vault Index.md
# shared flags: --overwrite (replace note), --index (rebuild index after write)
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
