"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from webscraper_core.fetchers.base import FetchResult

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str, url: str) -> FetchResult:
    html = (FIXTURES / name).read_text(encoding="utf-8")
    return FetchResult(url=url, final_url=url, status=200, html=html)


@pytest.fixture
def article_result() -> FetchResult:
    return load_fixture("article.html", "https://news.example.com/bakery-award")


@pytest.fixture
def contact_result() -> FetchResult:
    return load_fixture("contact.html", "https://acme.com/team/jane")


@pytest.fixture
def empty_result() -> FetchResult:
    return load_fixture("empty.html", "https://spa.example.com/app")
