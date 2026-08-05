"""Fetcher abstraction: turn a URL into raw HTML plus response metadata."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class FetchResult(BaseModel):
    """Outcome of a single fetch, handed to parsers."""

    url: str
    final_url: str
    status: int
    html: str
    fetched_at: datetime = Field(default_factory=_utcnow)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class BaseFetcher(ABC):
    """Async fetcher contract. Implementations reuse a session/browser across calls."""

    @abstractmethod
    async def fetch(self, url: str) -> FetchResult:
        """Retrieve ``url`` and return HTML + metadata. Raises on unrecoverable error."""

    async def aclose(self) -> None:  # noqa: B027  (optional hook, not abstract)
        """Release session/browser resources. Override where needed."""

    async def __aenter__(self) -> BaseFetcher:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
