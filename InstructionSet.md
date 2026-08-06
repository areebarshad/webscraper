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

## 2. The three scrape tasks

Every scrape needs a task (`--task`/`-t`) that decides how the page is parsed and
where the note lands.

| Task       | Use it for                              | Folder       | Extracts |
|------------|-----------------------------------------|--------------|----------|
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
uv run scraper scrape "<url>" --task contact
```

**Preview before writing** — inspect the parsed note without touching the vault:

```bash
uv run scraper scrape "<url>" --task contact --no-write
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
uv run scraper batch --file urls.txt --task contact
```

- Runs in parallel, politely. Tune with `-c/--concurrency` (default `5`).
- One bad URL never stops the rest — failures are reported per line, successes are
  written. Exit code is non-zero only if *every* URL failed.
- The index is rebuilt once at the end (if any note was written), not per URL.

---

## 6. Crawl a whole site (recursive multi-level)

`scrape` and `batch` each handle one page at a time. `crawl` starts at a **hub**
page — a faculty directory, a company team page, a product listing, a docs root, a
lecture outline — follows its in-content links, and scrapes every child page it
finds:

```bash
uv run scraper crawl "<seed-url>"                        # depth 1, auto-detect task
uv run scraper crawl "<seed-url>" --depth 2 --task contact
```

What you get out of one run:

- A **hub note** in `Hubs/<Seed Title>.md` — a map-of-content that lists every
  child it harvested as a `[[wikilink]]`.
- One **child note** per discovered page, filed in its normal category folder
  (`Contacts/`, `Profiles/`, `Research/`, ...). Every child gets a
  `parent: "[[Seed Title]]"` frontmatter key and a "Part of [[Seed Title]]"
  backlink, so the hub and its children form a connected cluster in Obsidian's
  graph.

How it decides what to follow and scrape:

- **Link discovery** harvests only in-content links. Navigation menus, footers,
  sidebars, `mailto:`/`tel:` links, on-page `#anchors`, and (by default) other
  domains are all ignored — you get the page's real subjects, not its chrome.
- **`--task auto`** (the default) classifies each child page on its own: a page
  with a contact email becomes a `contact`, and other pages fall back to a
  `profile`. Pass `--task contact` (or any task) to force one type for every child.

Crawl-specific flags:

| Flag | Default | Effect |
|------|---------|--------|
| `--depth <int>` | `1` | Levels of sub-links to follow. `1` = seed + its direct links; `2` also follows each child's links. |
| `--max-pages <int>` | `20` | Hard safety cap on how many pages a single run will scrape. |
| `--task <type\|auto>` | `auto` | Force a child task type, or infer it per page. |
| `--same-domain` / `--allow-external` | `--same-domain` | Stay on the seed's host, or follow links onto other domains. |

It also takes the shared flags below (`--dynamic`, `--overwrite`, `--index`,
`--vault`) and `-c/--concurrency`. It stays polite throughout — the same per-host
throttle, retry backoff, and `robots.txt` checks as every other command — never
scrapes the same URL twice in a run, and one bad page never aborts the crawl.

Defaults for `--depth`, `--max-pages`, and `--same-domain` come from the `crawl`
block in `config.yaml` (or `SCRAPER_CRAWL__*` env vars); the flags override them
per run.

---

## 7. Shared flags (scrape / person / batch / crawl)

| Flag | Effect |
|------|--------|
| `--dynamic` | Force the headless-browser fetcher (for JS-heavy pages). Normally the scraper escalates to it automatically when a static fetch comes back empty — only force it when you know the page needs JS. |
| `--overwrite` | Replace an existing note instead of writing a `" (2)"`-suffixed copy. |
| `--index` / `--no-index` | Force the `Index.md` rebuild on or off for this run, overriding the `auto_index` config default. |
| `--vault <path>` | Write to a different vault than the configured one. |

`--file` belongs to `batch` only; `-c/--concurrency` belongs to `batch` and
`crawl`.

---

## 8. The vault index

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

## 9. Graph connections

Notes are wired together on purpose so the graph view is useful, not a scatter of
islands:

- A **research** note links to the person's contact note via `[[Name]]`.
- Contacts, profiles, and research link their **company/institution** as `[[Org]]`,
  so colleagues at the same place share a hub. A bare domain (e.g. `example.com`)
  is left as plain text to avoid a junk hub node.
- A **crawl** hub note links to every child it harvested, and each child links
  back with a `parent` key and a backlink — the whole crawl becomes one cluster.

---

## 10. Choosing your vault

By default, notes go to the bundled `webscraper/` vault (already set up with the
category folders, a Welcome note, and a live Index). To use your own vault:

```bash
uv run scraper scrape "<url>" --task contact --vault /path/to/YourVault
```

Or set it permanently in `config.yaml`:

```yaml
vault_path: "/path/to/YourVault"
```

Category folders are created automatically on the first write.

---

## 11. AI fallback (optional, opt-in)

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

## 12. JavaScript-heavy sites

After the one-time Playwright setup (Section 1), the scraper renders JS pages in a
real headless browser automatically when a static fetch comes back empty. Force it
with `--dynamic` if you already know a page needs it. Without the `dynamic` extra
installed, such pages simply come back empty.

---

## 13. Configuration

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
| `crawl.default_depth` | `1` | Default `crawl` depth when `--depth` is omitted |
| `crawl.max_pages` | `20` | Default `crawl` page cap when `--max-pages` is omitted |
| `crawl.same_domain` | `true` | Whether `crawl` stays on the seed host by default |
| `llm.enabled` | `false` | AI fallback on/off |

---

## 14. Scrape responsibly

- `robots.txt` is honored by default. Leave it on. It can be disabled with
  `SCRAPER_FETCH__RESPECT_ROBOTS=false`, but only do so where you have the right.
- The per-host rate limiting and retry backoff are there to keep you a polite
  guest — don't crank the rate up carelessly.
- Only gather data you are allowed to access, and respect each site's terms.

---

## 15. Quick reference

```bash
uv run scraper tasks                                   # list task types
uv run scraper version                                 # installed version
uv run scraper scrape "<url>" -t contact               # one page → note
uv run scraper scrape "<url>" -t contact --no-write    # preview only
uv run scraper person "<url>"                          # contact + research
uv run scraper batch "<u1>" "<u2>" -t contact          # many pages
uv run scraper batch --file urls.txt -t contact        # from a file
uv run scraper crawl "<seed>"                          # recursive crawl (depth 1)
uv run scraper crawl "<seed>" --depth 2 --max-pages 40 # deeper, higher cap
uv run scraper index                                   # rebuild Index.md
uv run scraper --help                                  # full reference
```

Common exit codes: `1` = the URL(s) couldn't be scraped; `2` = a usage error
(unknown task, no URLs given).
