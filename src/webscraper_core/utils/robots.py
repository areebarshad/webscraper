"""robots.txt enforcement — a polite gate checked before fetching a URL.

Fetches and caches each host's robots.txt once, then answers allow/deny with the
standard-library parser. A missing or unreachable robots.txt means "allowed"
(the conventional default). Disabled entirely when ``respect_robots`` is off.
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from webscraper_core.utils.logging import get_logger
from webscraper_core.utils.useragent import pick_user_agent

log = get_logger(__name__)

# The user-agent token we present to robots rules. "*" matches the wildcard group.
_UA_TOKEN = "*"


class RobotsGate:
    """Caches per-host robots.txt and answers whether a URL may be fetched."""

    def __init__(self, enabled: bool, timeout: float = 10.0) -> None:
        self._enabled = enabled
        self._timeout = timeout
        self._cache: dict[str, RobotFileParser | None] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def allowed(self, url: str) -> bool:
        if not self._enabled:
            return True
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            return True  # file://, data://, etc. — nothing to check
        host = parts.netloc

        # One lock per host so concurrent URLs on different hosts don't serialize.
        async with self._guard:
            lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            if host not in self._cache:
                self._cache[host] = await self._load(parts.scheme, host)

        parser = self._cache[host]
        if parser is None:
            return True
        return parser.can_fetch(_UA_TOKEN, url)

    async def _load(self, scheme: str, host: str) -> RobotFileParser | None:
        robots_url = f"{scheme}://{host}/robots.txt"
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, follow_redirects=True
            ) as client:
                resp = await client.get(
                    robots_url, headers={"User-Agent": pick_user_agent()}
                )
        except httpx.HTTPError:
            return None  # unreachable robots.txt -> allow
        if resp.status_code >= 400:
            return None  # no robots.txt -> allow
        parser = RobotFileParser()
        parser.parse(resp.text.splitlines())
        return parser
