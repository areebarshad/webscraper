"""robots.txt gate tests with mocked robots responses (respx)."""

from __future__ import annotations

import httpx
import respx

from webscraper_core.utils.robots import RobotsGate

_ROBOTS = "User-agent: *\nDisallow: /private\n"


async def test_disabled_gate_allows_everything() -> None:
    gate = RobotsGate(enabled=False)
    assert await gate.allowed("https://example.com/private/secret") is True


async def test_non_http_scheme_allowed() -> None:
    gate = RobotsGate(enabled=True)
    assert await gate.allowed("file:///tmp/page.html") is True


@respx.mock
async def test_disallowed_path_blocked() -> None:
    respx.get("https://example.com/robots.txt").mock(
        return_value=httpx.Response(200, text=_ROBOTS)
    )
    gate = RobotsGate(enabled=True)
    assert await gate.allowed("https://example.com/private/x") is False
    assert await gate.allowed("https://example.com/public/x") is True


@respx.mock
async def test_missing_robots_allows() -> None:
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    gate = RobotsGate(enabled=True)
    assert await gate.allowed("https://example.com/anything") is True


@respx.mock
async def test_robots_fetched_once_and_cached() -> None:
    route = respx.get("https://example.com/robots.txt").mock(
        return_value=httpx.Response(200, text=_ROBOTS)
    )
    gate = RobotsGate(enabled=True)
    await gate.allowed("https://example.com/a")
    await gate.allowed("https://example.com/b")
    assert route.call_count == 1  # cached after first load
