"""Application settings: config.yaml defaults + environment-variable overrides.

Precedence (low -> high): config.yaml -> environment variables / .env.
Env vars use the SCRAPER_ prefix and __ for nesting, e.g. SCRAPER_FETCH__TIMEOUT=30.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

DEFAULT_CONFIG_PATH = Path("config.yaml")


class FetchSettings(BaseModel):
    timeout: float = 20.0
    connect_timeout: float = 10.0
    max_redirects: int = 5
    http2: bool = True
    respect_robots: bool = True
    rotate_user_agent: bool = True


class ThrottleSettings(BaseModel):
    rate: float = 1.0
    capacity: int = 3


class RetrySettings(BaseModel):
    max_attempts: int = 4
    base_delay: float = 0.5
    max_delay: float = 30.0


class DynamicSettings(BaseModel):
    block_resources: list[str] = Field(default_factory=lambda: ["image", "media", "font"])
    headless: bool = True


class LLMSettings(BaseModel):
    enabled: bool = False
    model: str = "claude-sonnet-5"
    max_tokens: int = 2048
    # Skip the LLM entirely when the cleaned page text is shorter than this
    # (404 pages, empty JS shells) — never pay for "no data found".
    min_chars: int = 400


class _YamlSource(PydanticBaseSettingsSource):
    """Loads defaults from a YAML file so config.yaml feeds the settings tree."""

    def __init__(self, settings_cls: type[BaseSettings], path: Path) -> None:
        super().__init__(settings_cls)
        self._path = path

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:  # noqa: ARG002
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        data = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        return data or {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    vault_path: Path = Path("webscraper")  # the bundled Obsidian vault
    contacts_dir: str = "Contacts"
    articles_dir: str = "Articles"
    profiles_dir: str = "Profiles"
    research_dir: str = "Research"
    overwrite_existing: bool = False
    auto_index: bool = True  # refresh Index.md after each scrape command

    fetch: FetchSettings = Field(default_factory=FetchSettings)
    throttle: ThrottleSettings = Field(default_factory=ThrottleSettings)
    retry: RetrySettings = Field(default_factory=RetrySettings)
    dynamic: DynamicSettings = Field(default_factory=DynamicSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Env / .env win over YAML defaults.
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            _YamlSource(settings_cls, DEFAULT_CONFIG_PATH),
            file_secret_settings,
        )

    @property
    def contacts_path(self) -> Path:
        return self.vault_path / self.contacts_dir

    @property
    def articles_path(self) -> Path:
        return self.vault_path / self.articles_dir


def load_settings() -> Settings:
    """Build a Settings instance from config.yaml + environment.

    Loads .env into the process environment first so downstream SDKs (e.g. the
    Anthropic client reading ANTHROPIC_API_KEY) see the same values.
    """
    from dotenv import load_dotenv

    load_dotenv()
    return Settings()
