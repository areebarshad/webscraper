"""User-Agent pool + matching headers for realistic, rotating requests."""

from __future__ import annotations

import random

# A small pool of current desktop browser UAs. Extend as needed.
USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
)

_BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
    "image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
}


def pick_user_agent() -> str:
    return random.choice(USER_AGENTS)


def headers_for(user_agent: str) -> dict[str, str]:
    """Build a header set carrying the given UA plus consistent accept headers."""
    return {**_BASE_HEADERS, "User-Agent": user_agent}


class UserAgentRotator:
    """Yields a UA per call, or a sticky one when rotation is disabled."""

    def __init__(self, rotate: bool = True) -> None:
        self._rotate = rotate
        self._sticky = pick_user_agent()

    def next(self) -> str:
        return pick_user_agent() if self._rotate else self._sticky

    def headers(self) -> dict[str, str]:
        return headers_for(self.next())
