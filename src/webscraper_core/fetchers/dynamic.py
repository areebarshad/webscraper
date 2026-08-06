"""Async Playwright fetcher for JS-rendered pages.

Lazy-imports playwright so the base install stays lightweight; install with the
``dynamic`` extra (``uv sync --extra dynamic`` + ``playwright install chromium``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from webscraper_core.config import Settings
from webscraper_core.fetchers.base import BaseFetcher, FetchResult
from webscraper_core.utils.retry import RetryPolicy, with_retry
from webscraper_core.utils.throttle import HostThrottler
from webscraper_core.utils.useragent import UserAgentRotator

if TYPE_CHECKING:
    from playwright.async_api import Browser, Playwright

# Mask the most obvious headless tell before any page script runs.
_STEALTH_JS = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"


class PlaywrightFetcher(BaseFetcher):
    """Render pages in headless Chromium. Browser launched lazily, reused per run."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._ua = UserAgentRotator(rotate=settings.fetch.rotate_user_agent)
        self._throttle = HostThrottler(settings.throttle.rate, settings.throttle.capacity)
        self._policy = RetryPolicy(
            max_attempts=settings.retry.max_attempts,
            base_delay=settings.retry.base_delay,
            max_delay=settings.retry.max_delay,
        )
        self._block = set(settings.dynamic.block_resources)

    async def _ensure_browser(self) -> Browser:
        if self._browser is None:
            from playwright.async_api import async_playwright

            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=self.settings.dynamic.headless)
        return self._browser

    async def _block_route(self, route: Any) -> None:
        if route.request.resource_type in self._block:
            await route.abort()
        else:
            await route.continue_()

    async def fetch(self, url: str) -> FetchResult:
        await self._throttle.acquire(url)
        browser = await self._ensure_browser()

        async def _do() -> FetchResult:
            context = await browser.new_context(
                user_agent=self._ua.next(),
                viewport={"width": 1366, "height": 900},
                locale="en-US",
            )
            await context.add_init_script(_STEALTH_JS)
            page = await context.new_page()
            try:
                if self._block:
                    await page.route("**/*", self._block_route)
                resp = await page.goto(
                    url, wait_until="networkidle", timeout=self.settings.fetch.timeout * 1000
                )
                html = await page.content()
                status = resp.status if resp else 0
                final_url = page.url
            finally:
                await context.close()
            return FetchResult(url=url, final_url=final_url, status=status or 200, html=html)

        return await with_retry(_do, self._policy)

    async def aclose(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._pw is not None:
            await self._pw.stop()
            self._pw = None
