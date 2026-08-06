"""Profile parser: extract public-profile details, with optional per-site hooks.

Generic extraction reads common metadata (Open Graph, headings, meta tags) and
social links. Site-specific parsing can be added by registering a hook keyed on
host in ``_SITE_HOOKS``.
"""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlsplit

from selectolax.parser import HTMLParser

from webscraper_core.fetchers.base import FetchResult
from webscraper_core.llm.anthropic_client import LLMExtractor
from webscraper_core.parsers.base import BaseParser
from webscraper_core.parsers.contact import _EMAIL, _SOCIAL_HOSTS, _dedup
from webscraper_core.schemas.llm import LLMProfile
from webscraper_core.schemas.profile import ProfileNote


def _meta(tree: HTMLParser, *names: str) -> str | None:
    for name in names:
        node = tree.css_first(f"meta[property='{name}'], meta[name='{name}']")
        if node:
            content = (node.attributes.get("content") or "").strip()
            if content:
                return content
    return None


def _socials(tree: HTMLParser) -> dict[str, str]:
    found: dict[str, str] = {}
    for a in tree.css("a[href]"):
        href = a.attributes.get("href") or ""
        host = urlsplit(href).netloc.lower().removeprefix("www.")
        label = _SOCIAL_HOSTS.get(host)
        if label and label not in found:
            found[label] = href
    return found


class ProfileParser(BaseParser):
    task = "profile"
    engine = "selectolax"

    def parse(self, res: FetchResult) -> ProfileNote | None:
        tree = HTMLParser(res.html)

        host = urlsplit(res.final_url).netloc.lower().removeprefix("www.")
        hook = _SITE_HOOKS.get(host)
        if hook is not None:
            return hook(tree, res)

        return self._generic(tree, res)

    def _generic(self, tree: HTMLParser, res: FetchResult) -> ProfileNote | None:
        name = _meta(tree, "og:title", "profile:username") or self._heading(tree)
        if not name:
            return None

        headline = _meta(tree, "og:description", "description")
        location = _meta(tree, "profile:location", "geo.placename")
        emails = _dedup(_EMAIL.findall(res.html))
        socials = _socials(tree)
        company = _meta(tree, "og:site_name")

        if not (headline or socials or emails):
            return None

        return ProfileNote(
            source_url=res.final_url,
            name=name,
            headline=headline,
            location=location,
            company=company,
            emails=emails,
            socials=socials,
        )

    async def llm_fallback(
        self, res: FetchResult, extractor: LLMExtractor
    ) -> ProfileNote | None:
        result = await extractor.extract(
            res,
            LLMProfile,
            "Extract the public profile on this page: name, headline/role, bio, "
            "location, company, and any email addresses.",
        )
        if result is None or not result.name.strip():
            return None
        if not (result.headline or result.bio or result.emails):
            return None
        return ProfileNote(
            source_url=res.final_url,
            name=result.name,
            headline=result.headline,
            bio=result.bio,
            location=result.location,
            company=result.company,
            emails=result.emails,
        )

    @staticmethod
    def _heading(tree: HTMLParser) -> str | None:
        for sel in ("h1", "title"):
            node = tree.css_first(sel)
            if node and node.text(strip=True):
                return node.text(strip=True)
        return None


# host -> parser hook. Empty by default; add site-specific extractors here.
_SITE_HOOKS: dict[str, Callable[[HTMLParser, FetchResult], ProfileNote | None]] = {}
