"""PlaywrightFetcher integration test. Skipped if playwright/chromium unavailable."""

from __future__ import annotations

from pathlib import Path

import pytest

from webscraper_core.config import Settings

playwright = pytest.importorskip("playwright.async_api")

from webscraper_core.fetchers.dynamic import PlaywrightFetcher  # noqa: E402

# A page whose real content is injected by JavaScript after load.
_JS_PAGE = """<!DOCTYPE html><html><head><title>SPA</title></head>
<body><div id="root"></div>
<script>
  document.getElementById('root').innerHTML =
    '<h1>Rendered Heading</h1><p>' + 'x'.repeat(600) + '</p>';
</script></body></html>"""


async def test_dynamic_fetch_runs_javascript(tmp_path: Path) -> None:
    page_file = tmp_path / "spa.html"
    page_file.write_text(_JS_PAGE, encoding="utf-8")

    s = Settings()
    s.dynamic.block_resources = []  # nothing to block on a local file
    fetcher = PlaywrightFetcher(s)
    try:
        res = await fetcher.fetch(page_file.as_uri())
    finally:
        await fetcher.aclose()

    assert "Rendered Heading" in res.html  # proves JS executed
    assert res.status == 200
