"""HTML noise removal + structured-data helpers.

Stripping scripts, styles, navigation, footers, and forms before either the rule
parsers scan text or the LLM sees a page (a) sharpens deterministic extraction
(no phone numbers pulled from a footer, no nav links counted as publications) and
(b) cuts LLM input tokens by ~80–90%. JSON-LD helpers let parsers read schema.org
data natively so the LLM is needed even less often.
"""

from __future__ import annotations

import json
from typing import Any

from selectolax.parser import HTMLParser

# Structural chrome that never contains the target data. Note: <header> is left
# in deliberately — many pages put the page <h1> inside it.
NOISE_SELECTORS = (
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "nav",
    "footer",
    "aside",
    "form",
    "iframe",
    '[role="navigation"]',
    '[role="banner"]',
    '[role="contentinfo"]',
    '[aria-hidden="true"]',
)


def strip_noise(tree: HTMLParser) -> HTMLParser:
    """Remove chrome nodes from ``tree`` in place and return it."""
    for node in tree.css(",".join(NOISE_SELECTORS)):
        node.decompose()
    return tree


def clean_text(html: str) -> str:
    """Visible text of ``html`` with scripts/nav/footer/etc. removed."""
    tree = strip_noise(HTMLParser(html))
    node = tree.body or tree.root
    return node.text(separator="\n", strip=True) if node else ""


def _href_values(tree: HTMLParser, prefix: str) -> list[str]:
    out: list[str] = []
    for a in tree.css(f"a[href^='{prefix}']"):
        href = a.attributes.get("href") or ""
        value = href.removeprefix(prefix).split("?")[0].strip()
        if value:
            out.append(value)
    return out


def mailto_addresses(tree: HTMLParser) -> list[str]:
    """Email addresses from ``mailto:`` links (reliable even when obfuscated in text)."""
    return _href_values(tree, "mailto:")


def tel_numbers(tree: HTMLParser) -> list[str]:
    """Phone numbers from ``tel:`` links."""
    return _href_values(tree, "tel:")


def _flatten(data: Any) -> list[dict[str, Any]]:
    """Flatten a JSON-LD payload (list, @graph, or single object) to dicts."""
    out: list[dict[str, Any]] = []
    if isinstance(data, list):
        for item in data:
            out.extend(_flatten(item))
    elif isinstance(data, dict):
        graph = data.get("@graph")
        if isinstance(graph, list):
            out.extend(_flatten(graph))
        else:
            out.append(data)
    return out


def jsonld_objects(tree: HTMLParser) -> list[dict[str, Any]]:
    """All JSON-LD objects embedded in ``<script type="application/ld+json">``."""
    objects: list[dict[str, Any]] = []
    for script in tree.css('script[type="application/ld+json"]'):
        raw = script.text()
        if not raw or not raw.strip():
            continue
        try:
            objects.extend(_flatten(json.loads(raw)))
        except (json.JSONDecodeError, ValueError):
            continue
    return objects


def _has_type(obj: dict[str, Any], type_name: str) -> bool:
    t = obj.get("@type")
    if isinstance(t, str):
        return t == type_name
    if isinstance(t, list):
        return type_name in t
    return False


def find_jsonld(tree: HTMLParser, type_name: str) -> dict[str, Any] | None:
    """First JSON-LD object of the given schema.org @type, if any."""
    for obj in jsonld_objects(tree):
        if _has_type(obj, type_name):
            return obj
    return None
