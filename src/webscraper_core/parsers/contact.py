"""Contact parser: regex-discover emails/phones, selectolax for name/company/socials."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlsplit

from selectolax.parser import HTMLParser

from webscraper_core.fetchers.base import FetchResult
from webscraper_core.llm.anthropic_client import LLMExtractor
from webscraper_core.parsers.base import BaseParser
from webscraper_core.schemas.contact import ContactNote
from webscraper_core.schemas.llm import LLMContact
from webscraper_core.utils.htmlclean import (
    clean_text,
    find_jsonld,
    mailto_addresses,
    tel_numbers,
)

# Common two-label public suffixes, so example.co.uk -> "Example", not "Co".
_MULTI_TLDS = frozenset(
    {
        "co.uk", "ac.uk", "org.uk", "gov.uk", "me.uk",
        "com.au", "net.au", "org.au", "edu.au", "gov.au",
        "co.nz", "co.za", "co.jp", "or.jp", "ne.jp",
        "com.br", "com.cn", "co.in", "ac.in", "edu.in",
    }
)

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


def _jsonld_list(value: Any) -> list[str]:
    """A JSON-LD field that may be a string, a list, or absent -> list of strings."""
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        return [v.strip() for v in value if isinstance(v, str) and v.strip()]
    return []


def _jsonld_name(person: dict[str, Any]) -> str | None:
    name = person.get("name")
    return name.strip() if isinstance(name, str) and name.strip() else None


class ContactParser(BaseParser):
    task = "contact"
    engine = "selectolax"

    def parse(self, res: FetchResult) -> ContactNote | None:
        tree = HTMLParser(res.html)
        person = find_jsonld(tree, "Person") or {}
        # Scan cleaned visible text (no nav/footer) so we don't harvest phone-like
        # numbers or emails from chrome — precision over raw-HTML recall.
        text = clean_text(res.html)

        emails = _dedup(
            [*_jsonld_list(person.get("email")), *mailto_addresses(tree), *_EMAIL.findall(text)]
        )
        phones = _dedup(
            [
                *_jsonld_list(person.get("telephone")),
                *tel_numbers(tree),
                *(p for p in (_clean_phone(m) for m in _PHONE.findall(text)) if p),
            ]
        )
        socials = self._socials(tree)

        if not (emails or phones or socials):
            return None

        return ContactNote(
            source_url=res.final_url,
            name=_jsonld_name(person) or self._name(tree, res.final_url),
            emails=emails,
            phones=phones,
            company=self._company(tree, person, res.final_url),
            socials=socials,
        )

    async def llm_fallback(
        self, res: FetchResult, extractor: LLMExtractor
    ) -> ContactNote | None:
        result = await extractor.extract(
            res,
            LLMContact,
            "Extract the contact / person described on this page: name, email "
            "addresses, phone numbers, company, and social profile links.",
        )
        if result is None or not result.name.strip():
            return None
        socials = {
            label: url
            for label, url in (
                ("linkedin", result.linkedin),
                ("twitter", result.twitter),
                ("github", result.github),
            )
            if url
        }
        if not (result.emails or result.phones or socials):
            return None
        return ContactNote(
            source_url=res.final_url,
            name=result.name,
            emails=result.emails,
            phones=result.phones,
            company=result.company,
            socials=socials,
        )

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
    def _company(tree: HTMLParser, person: dict[str, Any], url: str) -> str | None:
        works_for = person.get("worksFor")
        if isinstance(works_for, dict) and works_for.get("name"):
            return str(works_for["name"])
        if isinstance(works_for, str) and works_for.strip():
            return works_for
        meta = tree.css_first("meta[property='og:site_name']")
        if meta and meta.attributes.get("content"):
            return meta.attributes["content"]
        host = urlsplit(url).netloc.removeprefix("www.")
        if not host:
            return None
        parts = host.split(".")
        # The registrable label: skip a known two-label suffix (co.uk, com.au, ...).
        if len(parts) >= 3 and ".".join(parts[-2:]) in _MULTI_TLDS:
            sld = parts[-3]
        elif len(parts) >= 2:
            sld = parts[-2]
        else:
            sld = parts[0]
        return sld.title()
