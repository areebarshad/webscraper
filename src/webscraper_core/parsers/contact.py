"""Contact parser: regex-discover emails/phones, selectolax for name/company/socials."""

from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urlsplit

from selectolax.parser import HTMLParser

from webscraper_core.fetchers.base import FetchResult
from webscraper_core.parsers.base import BaseParser
from webscraper_core.schemas.contact import ContactNote

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Phones: optional +, groups of digits with spaces/dashes/parens/dots, 7-15 digits total.
_PHONE = re.compile(r"(?<![\w.])(\+?\d[\d\s().-]{6,}\d)(?![\w])")

# Social hosts we recognize -> label used in frontmatter/body.
_SOCIAL_HOSTS = {
    "linkedin.com": "linkedin",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "github.com": "github",
    "facebook.com": "facebook",
    "instagram.com": "instagram",
}


def _clean_phone(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw)
    if 7 <= len(digits) <= 15:
        return raw.strip()
    return None


def _dedup(seq: Iterable[str]) -> list[str]:
    seen: dict[str, None] = {}
    for item in seq:
        seen.setdefault(item, None)
    return list(seen)


class ContactParser(BaseParser):
    task = "contact"
    engine = "selectolax"

    def parse(self, res: FetchResult) -> ContactNote | None:
        tree = HTMLParser(res.html)
        body_text = tree.body.text(separator=" ", strip=True) if tree.body else ""

        emails = _dedup(_EMAIL.findall(self._raw_and_mailto(tree, res.html)))
        phones = _dedup(p for p in (_clean_phone(m) for m in _PHONE.findall(body_text)) if p)
        socials = self._socials(tree)

        if not (emails or phones or socials):
            return None

        name = self._name(tree, res.final_url)
        company = self._company(tree, res.final_url)

        return ContactNote(
            source_url=res.final_url,
            name=name,
            emails=emails,
            phones=phones,
            company=company,
            socials=socials,
        )

    @staticmethod
    def _raw_and_mailto(tree: HTMLParser, html: str) -> str:
        """Text to scan for emails: visible text plus mailto: hrefs."""
        mails = []
        for a in tree.css("a[href^='mailto:']"):
            href = a.attributes.get("href") or ""
            mails.append(href.removeprefix("mailto:").split("?")[0])
        return html + " " + " ".join(mails)

    @staticmethod
    def _socials(tree: HTMLParser) -> dict[str, str]:
        found: dict[str, str] = {}
        for a in tree.css("a[href]"):
            href = a.attributes.get("href") or ""
            host = urlsplit(href).netloc.lower().removeprefix("www.")
            label = _SOCIAL_HOSTS.get(host)
            if label and label not in found:
                found[label] = href
        return found

    @staticmethod
    def _name(tree: HTMLParser, url: str) -> str:
        for sel in ("h1", "title"):
            node = tree.css_first(sel)
            if node and node.text(strip=True):
                return node.text(strip=True)
        # Fall back to a readable path segment.
        seg = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
        return seg.replace("-", " ").replace("_", " ").title() or "Unknown"

    @staticmethod
    def _company(tree: HTMLParser, url: str) -> str | None:
        meta = tree.css_first("meta[property='og:site_name']")
        if meta and meta.attributes.get("content"):
            return meta.attributes["content"]
        host = urlsplit(url).netloc.removeprefix("www.")
        return host.split(".")[0].title() if host else None
