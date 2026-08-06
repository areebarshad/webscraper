# WebScraper Instruction Set

How to use WebScraper effectively. It fetches web pages and writes them as clean
Markdown notes into an Obsidian vault, sorted into folders and cross-linked for
the graph view.

---

## 1. Install

Requires **Python 3.11+** and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev                    # base install + dev tools
```

Add these two only if you need to scrape JavaScript-rendered sites:

```bash
uv sync --extra dev --extra dynamic    # adds Playwright
uv run playwright install chromium     # one-time browser download
```

All commands are run as `uv run scraper <command>`.

---

## 2. The four scrape tasks

Every scrape needs a task (`--task`/`-t`) that decides how the page is parsed and
where the note lands.

| Task       | Use it for                              | Folder       | Extracts |
|------------|-----------------------------------------|--------------|----------|
| `article`  | News stories, blog posts                | `Articles/`  | Title, author, date, clean body |
| `contact`  | A person's contact page / team bio      | `Contacts/`  | Emails, phones, company, socials |
| `profile`  | A public profile page                   | `Profiles/`  | Name, headline, bio, location |
| `research` | A researcher's publication list         | `Research/`  | Publications, each with a source link |

List them anytime with `uv run scraper tasks`.

Rule of thumb: pick the task by *what you want out of the page*, not by the site.
A faculty page can yield a `contact` note or a `research` note depending on the
task you pass — or use the `person` command to get both at once (Section 4).

---

## 3. Scrape a single page

```bash
uv run scraper scrape "<url>" --task article
```

**Preview before writing** — inspect the parsed note without touching the vault:

```bash
uv run scraper scrape "<url>" --task article --no-write
```

Use `--no-write` first whenever you are unsure a page will parse well. It runs the
full pipeline and prints the note, but writes nothing and skips the index rebuild.

---

## 4. Scrape a person (contact + research in one shot)

This is the headline feature. One command scrapes a single page into **two**
linked notes:

```bash
uv run scraper person "<faculty-or-bio-url>"
```

- `Contacts/<Name>.md` — email, company/department, phone, socials
- `Research/<Name> - Research.md` — every publication found, each linking to its
  source

The research note links back to the contact with a `[[Name]]` wikilink, so the two
resolve to each other in Obsidian's graph. If only one of the two can be extracted,
you still get that one; the command only fails if *nothing* is extractable.

---

## 5. Scrape many pages at once

Same task, many URLs — inline or from a file (one URL per line):

```bash
uv run scraper batch "<url1>" "<url2>" --task contact
uv run scraper batch --file urls.txt --task article
```

- Runs in parallel, politely. Tune with `-c/--concurrency` (default `5`).
- One bad URL never stops the rest — failures are reported per line, successes are
  written. Exit code is non-zero only if *every* URL failed.
- The index is rebuilt once at the end (if any note was written), not per URL.

---

## 6. Shared flags (scrape / person / batch)

| Flag | Effect |
|------|--------|
| `--dynamic` | Force the headless-browser fetcher (for JS-heavy pages). Normally the scraper escalates to it automatically when a static fetch comes back empty — only force it when you know the page needs JS. |
| `--overwrite` | Replace an existing note instead of writing a `" (2)"`-suffixed copy. |
| `--index` / `--no-index` | Force the `Index.md` rebuild on or off for this run, overriding the `auto_index` config default. |
| `--vault <path>` | Write to a different vault than the configured one. |

`--dynamic`, `--file`, and `-c` are only meaningful where listed; `--file` and
`-c` belong to `batch`.

---

## 7. The vault index

`Index.md` at the top of the vault is a map-of-content: one section per category,
listing every note as a clickable `[[link]]`.

- It **rebuilds automatically after every successful scrape** (`auto_index: true`
  in `config.yaml`).
- Turn it off for one run with `--no-index`, or globally with `auto_index: false`.
- Rebuild it manually anytime:

```bash
uv run scraper index
```

Skip the auto-rebuild (with `--no-index`) when doing a long sequence of individual
`scrape` calls, then run `scraper index` once at the end — rebuilding scans the
whole vault each time.

---

## 8. Graph connections

Notes are wired together on purpose so the graph view is useful, not a scatter of
islands:

- A **research** note links to the person's contact note via `[[Name]]`.
- Contacts, profiles, and research link their **company/institution** as `[[Org]]`,
  so colleagues at the same place share a hub. A bare domain (e.g. `example.com`)
  is left as plain text to avoid a junk hub node.
- **Articles** link their `[[Author]]`, grouping everything that author wrote.

---

## 9. Choosing your vault

By default, notes go to the bundled `webscraper/` vault (already set up with the
category folders, a Welcome note, and a live Index). To use your own vault:

```bash
uv run scraper scrape "<url>" --task article --vault /path/to/YourVault
```

Or set it permanently in `config.yaml`:

```yaml
vault_path: "/path/to/YourVault"
```

Category folders are created automatically on the first write.

---

## 10. AI fallback (optional, opt-in)

Most pages are handled by fast built-in rules. For pages too irregular for rules,
Claude can read the cleaned page text and extract structured data. It is **off by
default** and cost-guarded:

```bash
cp .env.example .env                 # paste your ANTHROPIC_API_KEY into .env
SCRAPER_LLM__ENABLED=true uv run scraper person "<url>"
```

Behavior worth knowing:

- Runs **only after** the free rule parsers return nothing.
- **Skips** near-empty pages (404s, blank JS shells) — controlled by `llm.min_chars`
  (default `400`) — so you never pay the AI to say "nothing here".
- Sees cleaned, stripped-down text, never raw HTML.
- Model is set by `llm.model` in `config.yaml`.

---

## 11. JavaScript-heavy sites

After the one-time Playwright setup (Section 1), the scraper renders JS pages in a
real headless browser automatically when a static fetch comes back empty. Force it
with `--dynamic` if you already know a page needs it. Without the `dynamic` extra
installed, such pages simply come back empty.

---

## 12. Configuration

Defaults live in `config.yaml`. Override any value without editing the file using
`SCRAPER_`-prefixed environment variables (`__` marks nesting):

```bash
SCRAPER_VAULT_PATH=~/Notes/Vault      # where notes are written
SCRAPER_THROTTLE__RATE=0.5            # 1 request every 2 seconds (gentler)
SCRAPER_LLM__ENABLED=true             # turn on the AI fallback
SCRAPER_FETCH__TIMEOUT=30             # longer request timeout
```

Keys you will actually touch:

| Config | Default | Meaning |
|--------|---------|---------|
| `vault_path` | `webscraper` | Where notes are written |
| `overwrite_existing` | `false` | Overwrite vs. write a numbered copy |
| `auto_index` | `true` | Rebuild `Index.md` after each scrape |
| `throttle.rate` | `1.0` | Requests per second, per host |
| `fetch.timeout` | `20.0` | Request timeout in seconds |
| `fetch.respect_robots` | `true` | Honor `robots.txt` |
| `llm.enabled` | `false` | AI fallback on/off |

---

## 13. Scrape responsibly

- `robots.txt` is honored by default. Leave it on. It can be disabled with
  `SCRAPER_FETCH__RESPECT_ROBOTS=false`, but only do so where you have the right.
- The per-host rate limiting and retry backoff are there to keep you a polite
  guest — don't crank the rate up carelessly.
- Only gather data you are allowed to access, and respect each site's terms.

---

## 14. Quick reference

```bash
uv run scraper tasks                                   # list task types
uv run scraper version                                 # installed version
uv run scraper scrape "<url>" -t article               # one page → note
uv run scraper scrape "<url>" -t article --no-write    # preview only
uv run scraper person "<url>"                          # contact + research
uv run scraper batch "<u1>" "<u2>" -t contact          # many pages
uv run scraper batch --file urls.txt -t article        # from a file
uv run scraper index                                   # rebuild Index.md
uv run scraper --help                                  # full reference
```

Common exit codes: `1` = the URL(s) couldn't be scraped; `2` = a usage error
(unknown task, no URLs given).
