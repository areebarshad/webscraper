"""Task-name -> parser class registry."""

from __future__ import annotations

from webscraper_core.parsers.article import ArticleParser
from webscraper_core.parsers.base import BaseParser
from webscraper_core.parsers.contact import ContactParser

_PARSERS: dict[str, type[BaseParser]] = {
    ArticleParser.task: ArticleParser,
    ContactParser.task: ContactParser,
}


def available_tasks() -> list[str]:
    return sorted(_PARSERS)


def get_parser(task: str) -> BaseParser:
    """Instantiate the parser registered for ``task``. Raises KeyError if unknown."""
    try:
        cls = _PARSERS[task]
    except KeyError:
        raise KeyError(
            f"unknown task {task!r}; available: {', '.join(available_tasks())}"
        ) from None
    return cls()
