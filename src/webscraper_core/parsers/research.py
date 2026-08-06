"""Research parser: gather a person's publications, each with a source link.

Rule-based extraction of academic publication lists is inherently messy, so this
does a best-effort pass (list items that look like publications) and leans on the
Claude LLM fallback for irregular pages.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from selectolax.parser import HTMLParser

from webscraper_core.fetchers.base import FetchResult
from webscraper_core.llm.anthropic_client import LLMExtractor
from webscraper_core.parsers.base import BaseParser
from webscraper_core.schemas.llm import LLMResearch
from webscraper_core.schemas.research import ResearchItem, ResearchNote
from webscraper_core.utils.htmlclean import strip_noise

_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_MIN_TITLE = 20  # publication titles are long; filters nav/menu noise


class ResearchParser(BaseParser):
    task = "research"
    engine = "selectolax"

    def parse(self, res: FetchResult) -> ResearchNote | None:
        tree = HTMLParser(res.html)
        name = self._name(tree, res.final_url)  # before stripping (h1 may sit in header)
        strip_noise(tree)  # drop nav/footer/scripts so they aren't counted as items
        items = self._items(tree, res.final_url)
        if not items:
            return None
        return ResearchNote(
            source_url=res.final_url,
            name=name,
            affiliation=self._affiliation(tree, res.final_url),
            items=items,
        )

    async def llm_fallback(
        self, res: FetchResult, extractor: LLMExtractor
    ) -> ResearchNote | None:
        result = await extractor.extract(
            res,
            LLMResearch,
            "Extract this researcher's publications and research works. For each, "
            "capture the title, a source link if present, the year, and the venue.",
        )
        if result is None or not result.name.strip():
            return None
        items = [
            ResearchItem(
                title=it.title, url=it.url, year=it.year, venue=it.venue, summary=it.summary
            )
            for it in result.items
            if it.title.strip()
        ]
        if not items:
            return None
        return ResearchNote(
            source_url=res.final_url,
            name=result.name,
            affiliation=result.affiliation,
            items=items,
        )

    @staticmethod
    def _items(tree: HTMLParser, base_url: str) -> list[ResearchItem]:
        items: list[ResearchItem] = []
        seen: set[str] = set()
        for li in tree.css("li, p"):
            text = li.text(separator=" ", strip=True)
            if not text or len(text) < _MIN_TITLE:
                continue
            # Keep entries that look like publications: long text with a year or a link.
            link = li.css_first("a[href]")
            has_year = bool(_YEAR.search(text))
            if not (link or has_year):
                continue
            key = text[:120].lower()
            if key in seen:
                continue
            seen.add(key)
            url = None
            if link and (href := link.attributes.get("href")):
                url = urljoin(base_url, href)
            year_match = _YEAR.search(text)
            items.append(
                ResearchItem(
                    title=text[:300],
                    url=url,
                    year=int(year_match.group()) if year_match else None,
                )
            )
            if len(items) >= 200:
                break
        return items

    @staticmethod
    def _name(tree: HTMLParser, url: str) -> str:
        for sel in ("h1", "title"):
            node = tree.css_first(sel)
            if node and node.text(strip=True):
                return node.text(strip=True)
        seg = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
        return seg.replace("-", " ").replace("_", " ").title() or "Unknown"

    @staticmethod
    def _affiliation(tree: HTMLParser, url: str) -> str | None:
        meta = tree.css_first("meta[property='og:site_name']")
        if meta and meta.attributes.get("content"):
            return meta.attributes["content"]
        host = urlsplit(url).netloc.removeprefix("www.")
        return host or None
