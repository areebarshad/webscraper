"""Async exponential-backoff retry with jitter for transient fetch failures."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

import httpx

T = TypeVar("T")

# Status codes worth retrying: rate-limit + transient server errors.
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


class RetryableStatus(Exception):
    """Raised by a fetch body to signal a retryable HTTP status.

    Carries the server's Retry-After hint (seconds) when present so backoff can
    honor it instead of the computed delay.
    """

    def __init__(self, status: int, retry_after: float | None = None) -> None:
        super().__init__(f"retryable status {status}")
        self.status = status
        self.retry_after = retry_after


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 4
    base_delay: float = 0.5
    max_delay: float = 30.0

    def backoff(self, attempt: int) -> float:
        """Delay before the given 0-indexed attempt: base * 2**attempt + jitter."""
        raw = self.base_delay * (2**attempt)
        raw = min(raw, self.max_delay)
        return float(raw + random.uniform(0, raw / 2))


# Transport-level errors that are safe to retry.
_TRANSIENT = (httpx.TransportError, httpx.RemoteProtocolError)


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
) -> T:
    """Call ``fn`` with retries. ``fn`` should raise RetryableStatus or a
    transient httpx error to trigger a retry; other exceptions propagate."""
    last_exc: Exception | None = None
    for attempt in range(policy.max_attempts):
        try:
            return await fn()
        except RetryableStatus as exc:
            last_exc = exc
            if attempt == policy.max_attempts - 1:
                break
            delay = exc.retry_after if exc.retry_after is not None else policy.backoff(attempt)
            await asyncio.sleep(delay)
        except _TRANSIENT as exc:
            last_exc = exc
            if attempt == policy.max_attempts - 1:
                break
            await asyncio.sleep(policy.backoff(attempt))
    assert last_exc is not None
    raise last_exc
