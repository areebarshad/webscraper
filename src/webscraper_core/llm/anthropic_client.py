"""Claude structured-output extractor used as a parser fallback.

Opt-in and cost-guarded: does nothing unless ``llm.enabled`` is set and an API
key is available. Sends readable page text (not raw HTML) to bound token spend,
and returns a validated instance of the caller's Pydantic schema, or ``None`` on
refusal / error / disabled.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, TypeVar

import trafilatura
from pydantic import BaseModel

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

from webscraper_core.config import LLMSettings
from webscraper_core.fetchers.base import FetchResult
from webscraper_core.utils.htmlclean import clean_text
from webscraper_core.utils.logging import get_logger

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# Cap the text sent to the model to keep token cost predictable.
_MAX_TEXT_CHARS = 12_000


def readable_text(res: FetchResult) -> str:
    """Clean, noise-free page text for the model — never raw HTML.

    trafilatura's article extraction first (strips boilerplate); if it finds
    nothing, fall back to visible text with scripts/nav/footer/forms stripped.
    Either way the model never sees markup, scripts, or chrome.
    """
    extracted = trafilatura.extract(res.html, url=res.final_url, favor_recall=True)
    text = extracted or clean_text(res.html)
    return text[:_MAX_TEXT_CHARS]


class LLMExtractor:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings
        # lazily built so the SDK import is paid only when used
        self._client: AsyncAnthropic | None = None

    @property
    def enabled(self) -> bool:
        return self.settings.enabled and bool(os.environ.get("ANTHROPIC_API_KEY"))

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic()
        return self._client

    async def extract(self, res: FetchResult, schema: type[T], instruction: str) -> T | None:
        """Extract ``schema`` from the page, or None if disabled/refused/failed."""
        if not self.enabled:
            return None

        text = readable_text(res)
        if len(text) < self.settings.min_chars:
            # 404 pages / empty JS shells — don't pay the model to find nothing.
            log.info(
                "skipping LLM: only %d chars of content (min %d) at %s",
                len(text),
                self.settings.min_chars,
                res.final_url,
            )
            return None

        client = self._get_client()
        try:
            response = await client.messages.parse(
                model=self.settings.model,
                max_tokens=self.settings.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"{instruction}\n\n"
                            f"Source URL: {res.final_url}\n\n"
                            f"Page content:\n{text}"
                        ),
                    }
                ],
                output_format=schema,
            )
        except Exception as exc:  # noqa: BLE001  (fallback must never crash the pipeline)
            log.warning("LLM extraction failed: %s", exc)
            return None

        if response.stop_reason == "refusal":
            log.warning("LLM extraction refused for %s", res.final_url)
            return None
        return response.parsed_output
