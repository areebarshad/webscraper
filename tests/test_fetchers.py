"""HttpxFetcher tests with mocked transport (respx)."""

from __future__ import annotations

import httpx
import pytest
import respx

from webscraper_core.config import Settings
from webscraper_core.fetchers.static import HttpxFetcher


def _fast_settings() -> Settings:
    s = Settings()
    # Speed up: no real backoff waits, generous throttle.
    s.retry.base_delay = 0.0
    s.retry.max_delay = 0.0
    s.throttle.rate = 1000.0
    s.throttle.capacity = 1000
    s.fetch.http2 = False  # respx transport doesn't negotiate h2
    return s


@respx.mock
async def test_fetch_success() -> None:
    respx.get("https://example.com/page").mock(
        return_value=httpx.Response(200, html="<h1>hi</h1>")
    )
    fetcher = HttpxFetcher(_fast_settings())
    try:
        res = await fetcher.fetch("https://example.com/page")
    finally:
        await fetcher.aclose()
    assert res.status == 200
    assert "hi" in res.html


@respx.mock
async def test_fetch_retries_on_503_then_succeeds() -> None:
    route = respx.get("https://example.com/flaky").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, html="<h1>ok</h1>"),
        ]
    )
    fetcher = HttpxFetcher(_fast_settings())
    try:
        res = await fetcher.fetch("https://example.com/flaky")
    finally:
        await fetcher.aclose()
    assert res.status == 200
    assert route.call_count == 2


@respx.mock
async def test_fetch_exhausts_retries_and_raises() -> None:
    respx.get("https://example.com/down").mock(return_value=httpx.Response(500))
    s = _fast_settings()
    s.retry.max_attempts = 2
    fetcher = HttpxFetcher(s)
    from webscraper_core.utils.retry import RetryableStatus

    with pytest.raises(RetryableStatus):
        try:
            await fetcher.fetch("https://example.com/down")
        finally:
            await fetcher.aclose()


@respx.mock
async def test_user_agent_header_sent() -> None:
    route = respx.get("https://example.com/ua").mock(
        return_value=httpx.Response(200, html="<p>x</p>")
    )
    fetcher = HttpxFetcher(_fast_settings())
    try:
        await fetcher.fetch("https://example.com/ua")
    finally:
        await fetcher.aclose()
    sent_ua = route.calls.last.request.headers.get("user-agent", "")
    assert "Mozilla/5.0" in sent_ua
