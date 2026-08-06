---
type: home
tags: [home, moc]
---

# 🕸️ Scraper Vault

This vault is filled automatically by the **WebScraper → Obsidian** tool. Every
page you scrape becomes a clean Markdown note, filed in the right folder and
linked into your graph.

## Folders

- 📰 **[[Articles]]** — news and articles: title, author, date, clean body.
- 👤 **[[Contacts]]** — a person's contact info: emails, phones, company, socials.
- 🧑‍💼 **[[Profiles]]** — public profiles: name, headline, bio, location.
- 🔬 **[[Research]]** — a person's publications, each linking to its source.

## Start here

- **[[Index]]** — a live map of everything scraped so far, grouped by folder.

## How notes connect

Scraping a person (e.g. a professor) creates two linked notes: their details in
**Contacts/** and their publications in **Research/**. Both carry a `[[Name]]`
wikilink, so they resolve to each other in the graph — open one and you're one
click from the other.

## Adding to the vault

From the project root:

```bash
uv run scraper scrape "<url>" --task article    # one page
uv run scraper person "<faculty-url>"           # contact + research
uv run scraper batch --file urls.txt --task contact
uv run scraper index                            # refresh [[Index]]
```

Notes land here automatically because `vault_path` in `config.yaml` points at this
folder. Point it elsewhere (or pass `--vault /path/to/YourVault`) to use a
different vault.
