# WebScraper → Obsidian 🕸️📓

**Turn any web page into a clean, organized note in your Obsidian vault — in one command.**

Point it at a news article, a company team page, or a professor's faculty
profile, and it pulls out what matters, tidies it into Markdown with proper tags
and links, and files it in the right folder of your vault. No copy‑paste, no
messy formatting, no dead ends when a site is built with heavy JavaScript.

It's open source, runs entirely on your machine, and is friendly to the sites it
visits.

---

## Why you'll like it

- **📥 Straight into Obsidian.** Every result is a real `.md` note with YAML
  frontmatter, tags, and `[[wikilinks]]` — it shows up in your graph immediately.
- **🗂️ Sorts itself.** Articles go in `Articles/`, people in `Contacts/`,
  profiles in `Profiles/`, and research in `Research/`. You don't organize
  anything.
- **👤 Knows people.** Scrape a professor once and get **two** linked notes: their
  contact details *and* a list of their publications, each with a link back to
  where it was found.
- **🧠 Smart fallback, used sparingly.** When a page is messy or unusual, it can
  call in Claude (Anthropic's AI) to read it and extract clean, structured data —
  but only if you turn it on, only after the free built‑in rules come up empty,
  and never for near‑empty pages (404s or blank shells are skipped, so you never
  pay the AI to say "nothing here"). When it does run, it sees clean, stripped‑
  down text — no scripts or clutter — keeping it fast and cheap.
- **🌐 Handles modern sites.** Static pages are fetched fast; JavaScript‑heavy
  pages are rendered in a real browser automatically when needed.
- **🗺️ A living index.** An `Index.md` map-of-content links every note by
  category and **refreshes itself after every scrape** — never stale, never
  hand-maintained.
- **🔗 A graph that connects.** A person's publications link to their contact
  note, colleagues share a company/institution hub, and article authors become
  hubs — so Obsidian's graph view is actually meaningful, not a scatter of islands.
- **🤝 A polite guest.** Obeys each site's `robots.txt`, rotates browser
  identities, spaces out requests per site, and retries gently — so it behaves
  like a considerate visitor, not a hammer.
- **🔒 Yours, locally.** Your notes stay in your vault on your computer. Nothing is
  uploaded anywhere unless you explicitly enable the AI fallback.

---

## Quick start

You'll need **Python 3.11+** and [uv](https://docs.astral.sh/uv/) (a fast Python
package manager).

```bash
uv sync --extra dev            # install everything
```

Then scrape something:

```bash
# Save a news article as a note
uv run scraper scrape "https://example.com/some-article" --task article

# Grab someone's contact details
uv run scraper scrape "https://example.com/team/jane" --task contact

# Peek at the note first without saving it
uv run scraper scrape "https://example.com/some-article" --task article --no-write
```

Your notes appear inside the bundled Obsidian vault at `webscraper/` — already set
up with `Articles/`, `Contacts/`, `Profiles/`, and `Research/` folders, a
**Welcome** note, and a live **Index**. Open that folder as a vault in Obsidian
and everything is there. Want to use your **own** vault instead? Add
`--vault /path/to/YourVault` to any command, or set `vault_path` in `config.yaml`
(the scraper creates the category folders automatically on first write).

---

## The people workflow ✨

This is the standout feature. Say you're researching **Professor X**:

```bash
uv run scraper person "https://university.edu/faculty/professor-x"
```

You get two notes, automatically linked together:

- **`Contacts/Professor X.md`** — email, department/company, phone, social links
- **`Research/Professor X - Research.md`** — every publication it can find, each
  with a link to its source

Open either one in Obsidian and the `[[Professor X]]` link ties them together in
your graph. Build a research library one person at a time.

---

## Scrape a whole list at once

Have a page full of links, or a file of URLs? Do them all in one go:

```bash
# Several URLs
uv run scraper batch "https://a.com" "https://b.com" --task article

# Or from a file (one URL per line)
uv run scraper batch --file urls.txt --task contact
```

It runs them in parallel (politely), writes a note for each success, and tells
you which ones didn't pan out — one bad link never stops the rest.

Handy flags on `scrape`, `person`, and `batch`: `--overwrite` (replace an existing
note instead of making a numbered copy) and `--index` (refresh the vault index
right after writing).

See everything it can do:

```bash
uv run scraper tasks       # list the scrape types: article, contact, profile, research
uv run scraper --help      # full command reference
```

---

## One map for your whole vault 🗺️

Every scrape **automatically refreshes** `Index.md` at the top of your vault — a
section per category (Articles, Contacts, Profiles, Research) listing every note
as a clickable `[[link]]`. Open it in Obsidian and everything is one hop away; you
never have to maintain it.

Prefer to do it by hand? Rebuild it anytime with `uv run scraper index`, or turn
the automatic refresh off per‑run with `--no-index` (or set `auto_index: false`
in `config.yaml`).

### A graph that actually connects

Notes are wired together on purpose, so Obsidian's graph view is genuinely
useful:

- Scrape a **person** and their research note links straight to their contact
  note, so their details and their publications sit together in the graph.
- Everyone at the same **company or institution** links to a shared hub note, so
  colleagues cluster together.
- Article **authors** become hubs too, grouping everything they wrote.

---

## Turning on the AI fallback (optional)

Most pages are handled by fast, built‑in rules. For the occasional page that's
too irregular for rules, you can let Claude read it and extract the data for you.
It's **off by default** — enable it only when you want it:

```bash
cp .env.example .env         # then paste your ANTHROPIC_API_KEY into .env
SCRAPER_LLM__ENABLED=true uv run scraper person "https://university.edu/faculty/professor-x"
```

When enabled, the AI only steps in *after* the free built‑in rules come up empty,
so you're never paying for pages that scrape cleanly on their own.

---

## Handling JavaScript‑heavy sites

Some sites render their content in the browser with JavaScript. If a normal fetch
comes back empty, the scraper can render the page in a real headless browser and
try again. Set that up once:

```bash
uv sync --extra dev --extra dynamic
uv run playwright install chromium
```

Then it just works — the scraper escalates to the browser on its own, or you can
force it with `--dynamic`.

---

## Configuration

Sensible defaults live in `config.yaml` — folder names, politeness (request
rate), timeouts, and the AI model. Override any of it without editing files using
`SCRAPER_`‑prefixed environment variables, for example:

```bash
SCRAPER_VAULT_PATH=~/Notes/Vault      # where notes are written
SCRAPER_THROTTLE__RATE=0.5            # go gentler: 1 request every 2 seconds
SCRAPER_LLM__ENABLED=true             # turn on the AI fallback
```

---

## Please scrape responsibly

This tool is for gathering information you're allowed to access. It **honors
`robots.txt` by default** — if a site asks crawlers to stay out of a path, the
scraper won't fetch it. Beyond that: respect each site's terms of service, don't
hammer servers, and don't collect personal data you have no right to. The
built‑in rate limiting and `robots.txt` checks are there to help you be a good
citizen — please keep them on. (You can disable the robots check with
`SCRAPER_FETCH__RESPECT_ROBOTS=false`, but think twice before you do.)

---

## Contributing

Adding a new kind of note is a small, well‑defined job — a schema, a parser, and
a folder. See **CLAUDE.md** for the project map and the exact extension pattern,
and run the checks before opening a pull request:

```bash
uv run pytest && uv run ruff check && uv run mypy src
```

## License

MIT — free to use, modify, and share.
