"""Link-discovery tests: in-content harvesting, junk filtering, dedup."""

from __future__ import annotations

from webscraper_core.fetchers.discovery import discover_links

_HTML = """
<html><body>
<nav><a href="/nav-home">Home</a></nav>
<h1>Physics Faculty</h1>
<main>
  <a href="/faculty/alice">Alice</a>
  <a href="faculty/bob">Bob</a>
  <a href="/faculty/alice#pubs">Alice (anchor dup)</a>
  <a href="https://twitter.com/dept">tweet</a>
  <a href="mailto:x@dept.edu">mail</a>
  <a href="tel:+123456789">call</a>
  <a href="#top">to top</a>
</main>
<footer><a href="/privacy">Privacy</a></footer>
</body></html>
"""

_BASE = "https://dept.edu/faculty"


def test_discovers_only_in_content_same_domain_links() -> None:
    links = discover_links(_HTML, _BASE, same_domain=True)
    assert links == [
        "https://dept.edu/faculty/alice",
        "https://dept.edu/faculty/bob",
    ]


def test_strips_nav_footer_mailto_tel_and_anchors() -> None:
    links = discover_links(_HTML, _BASE, same_domain=True)
    joined = " ".join(links)
    assert "nav-home" not in joined  # nav stripped
    assert "privacy" not in joined  # footer stripped
    assert "mailto" not in joined and "tel:" not in joined
    assert "twitter.com" not in joined  # external dropped
    assert all("#" not in link for link in links)  # fragments removed


def test_allow_external_includes_other_hosts() -> None:
    links = discover_links(_HTML, _BASE, same_domain=False)
    assert "https://twitter.com/dept" in links


def test_seed_url_is_never_returned() -> None:
    html = '<main><a href="/faculty/">self</a><a href="/faculty/x">child</a></main>'
    links = discover_links(html, "https://dept.edu/faculty", same_domain=True)
    assert links == ["https://dept.edu/faculty/x"]
