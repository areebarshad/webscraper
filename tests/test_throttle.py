"""Tests for the async token-bucket throttler."""

from __future__ import annotations

import asyncio
import time

import pytest

from webscraper_core.utils.throttle import HostThrottler, TokenBucket


async def test_burst_capacity_is_immediate() -> None:
    bucket = TokenBucket(rate=1.0, capacity=3)
    start = time.monotonic()
    for _ in range(3):
        await bucket.acquire()
    # Three tokens are pre-filled; no meaningful wait.
    assert time.monotonic() - start < 0.1


async def test_refill_forces_wait() -> None:
    bucket = TokenBucket(rate=10.0, capacity=1)
    await bucket.acquire()  # empties the bucket
    start = time.monotonic()
    await bucket.acquire()  # must wait ~0.1s for a refill
    assert time.monotonic() - start >= 0.08


async def test_invalid_params() -> None:
    with pytest.raises(ValueError):
        TokenBucket(rate=0, capacity=1)
    with pytest.raises(ValueError):
        TokenBucket(rate=1, capacity=0)


async def test_host_throttler_isolates_hosts() -> None:
    throttler = HostThrottler(rate=10.0, capacity=1)
    # Different hosts have independent buckets -> both immediate.
    start = time.monotonic()
    await asyncio.gather(
        throttler.acquire("https://a.example/x"),
        throttler.acquire("https://b.example/y"),
    )
    assert time.monotonic() - start < 0.1
