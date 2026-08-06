"""Tests for HTML noise removal + JSON-LD helpers."""

from __future__ import annotations

from selectolax.parser import HTMLParser

from webscraper_core.utils.htmlclean import (
    clean_text,
    find_jsonld,
    mailto_addresses,
    strip_noise,
    tel_numbers,
)

_PAGE = """
<html><head>
  <style>.x{color:red}</style>
  <script>var tracking = 1;</script>
  <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Person","name":"Jane Doe",
     "email":"jane@acme.com","telephone":"+1-555-0100",
     "worksFor":{"@type":"Organization","name":"Acme Corp"}}
  </script>
</head><body>
  <nav><a href="/home">Home</a><a href="/about">About</a></nav>
  <main><h1>Jane Doe</h1><p>The real content lives here.</p>
    <a href="mailto:jane@acme.com">Email</a>
    <a href="tel:+15550100">Call</a></main>
  <footer>Copyright 2026 · Privacy · Terms</footer>
</body></html>
"""


def test_clean_text_drops_chrome() -> None:
    text = clean_text(_PAGE)
    assert "The real content lives here." in text
    assert "Home" not in text  # nav stripped
    assert "Copyright 2026" not in text  # footer stripped
    assert "tracking" not in text  # script stripped


def test_strip_noise_is_in_place() -> None:
    tree = HTMLParser(_PAGE)
    assert tree.css_first("nav") is not None
    strip_noise(tree)
    assert tree.css_first("nav") is None
    assert tree.css_first("footer") is None
    assert tree.css_first("main") is not None


def test_find_jsonld_person() -> None:
    person = find_jsonld(HTMLParser(_PAGE), "Person")
    assert person is not None
    assert person["name"] == "Jane Doe"
    assert person["worksFor"]["name"] == "Acme Corp"


def test_mailto_and_tel_helpers() -> None:
    tree = HTMLParser(_PAGE)
    assert mailto_addresses(tree) == ["jane@acme.com"]
    assert tel_numbers(tree) == ["+15550100"]
