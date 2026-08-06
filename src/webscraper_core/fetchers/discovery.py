"""Link-discovery engine: harvest relevant sub-links from a container page.

Used by the recursive ``crawl`` mode to find child pages under a seed (a faculty
list, team page, product directory, docs root, ...). It leans on the shared
``htmlclean.strip_noise`` cleaner so navigation menus, footers, sidebars, and
forms are dropped *before* links are collected — the same nodes the rule parsers
already treat as chrome. What remains are the in-content links that actually
point at the page's subjects.

Junk that is filtered out:
  * navigation / footer / aside / form links (removed by ``strip_noise``);
  * pure in-page anchors (``#section``) and ``mailto:`` / ``tel:`` / ``javascript:``;
  * external hosts (unless ``same_domain=False``);
  * the seed URL itself and any duplicate (order-preserving dedup).
"""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit, urlunsplit

from selectolax.parser import HTMLParser

from webscraper_core.utils.htmlclean import strip_noise

_SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "sms:", "ftp:")


def _host(netloc: str) -> str:
    """Comparable host: lower-cased, without a port or a leading ``www.``."""
    return netloc.lower().split(":", 1)[0].removeprefix("www.")


def _normalize(url: str) -> str:
    """Canonical key for dedup: drop fragment, lower-case scheme/host, trim a
    trailing slash on the path so ``/a`` and ``/a/`` are the same page."""
    parts = urlsplit(url)
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def discover_links(html: str, base_url: str, *, same_domain: bool = True) -> list[str]:
    """Return in-content sub-links found on ``html``, resolved against ``base_url``.

    Order-preserving and de-duplicated. The seed (``base_url``) is never returned.
    """
    tree = strip_noise(HTMLParser(html))
    base_host = _host(urlsplit(base_url).netloc)

    seen: set[str] = {_normalize(base_url)}
    out: list[str] = []

    for anchor in tree.css("a[href]"):
        href = (anchor.attributes.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        if href.lower().startswith(_SKIP_SCHEMES):
            continue

        absolute = urljoin(base_url, href)
        parts = urlsplit(absolute)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            continue
        if same_domain and _host(parts.netloc) != base_host:
            continue

        clean = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
        key = _normalize(clean)
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)

    return out
