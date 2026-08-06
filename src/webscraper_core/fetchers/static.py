"""Async static fetcher over a reused httpx client: UA rotation, throttle, retry."""

from __future__ import annotations

import httpx

from webscraper_core.config import Settings
from webscraper_core.fetchers.base import BaseFetcher, FetchResult
from webscraper_core.utils.retry import RETRY_STATUS, RetryableStatus, RetryPolicy, with_retry
from webscraper_core.utils.throttle import HostThrottler
from webscraper_core.utils.useragent import UserAgentRotator


class HttpxFetcher(BaseFetcher):
    """Fetch static HTML. One AsyncClient (cookies + pool + HTTP/2) reused per run."""

    def __init__(self, settings: Settings) -> None:
        f = settings.fetch
        self._client = httpx.AsyncClient(
            http2=f.http2,
            follow_redirects=True,
            max_redirects=f.max_redirects,
            timeout=httpx.Timeout(f.timeout, connect=f.connect_timeout),
        )
        self._ua = UserAgentRotator(rotate=f.rotate_user_agent)
        self._throttle = HostThrottler(settings.throttle.rate, settings.throttle.capacity)
        self._policy = RetryPolicy(
            max_attempts=settings.retry.max_attempts,
            base_delay=settings.retry.base_delay,
            max_delay=settings.retry.max_delay,
        )

    async def fetch(self, url: str) -> FetchResult:
        await self._throttle.acquire(url)

        async def _do() -> FetchResult:
            resp = await self._client.get(url, headers=self._ua.headers())
            if resp.status_code in RETRY_STATUS:
                raise RetryableStatus(resp.status_code, _retry_after(resp))
            resp.raise_for_status()
            return FetchResult(
                url=url,
                final_url=str(resp.url),
                status=resp.status_code,
                html=resp.text,
            )

        return await with_retry(_do, self._policy)

    async def aclose(self) -> None:
        await self._client.aclose()


def _retry_after(resp: httpx.Response) -> float | None:
    raw = resp.headers.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None  # HTTP-date form: ignore, fall back to computed backoff
