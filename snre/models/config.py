# Author: Bradley R. Kinnard
"""
SNREConfig -- validated configuration via pydantic-settings.
Supports env overrides (SNRE_ prefix), YAML file loading, and .env files.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic import ValidationError
from pydantic_settings import BaseSettings
from pydantic_settings import PydanticBaseSettingsSource
from pydantic_settings import SettingsConfigDict


class _YamlSettingsSource(PydanticBaseSettingsSource):
    """Load config from a YAML file if it exists."""

    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        self._yaml_data: dict[str, Any] = {}
        yaml_path = Path("config/settings.yaml")
        if yaml_path.exists():
            raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
            # flatten nested YAML sections into top-level keys
            for section_val in raw.values():
                if isinstance(section_val, dict):
                    self._yaml_data.update(section_val)

    def get_field_value(
        self, field: Any, field_name: str
    ) -> tuple[Any, str, bool]:
        val = self._yaml_data.get(field_name)
        return val, field_name, val is not None

    def __call__(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for field_name in self.settings_cls.model_fields:
            val, _, found = self.get_field_value(None, field_name)
            if found:
                result[field_name] = val
        return result


class SNREConfig(BaseSettings):
    """System configuration with env overrides, YAML loading, and .env support."""

    model_config = SettingsConfigDict(
        env_prefix="SNRE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    max_concurrent_agents: int = Field(default=5, ge=1, le=50)
    consensus_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    max_iterations: int = Field(default=10, ge=1, le=100)
    timeout_seconds: int = Field(default=300, ge=10)
    enable_evolution_log: bool = True
    snapshot_frequency: int = Field(default=5, ge=1)
    max_snapshots: int = Field(default=100, ge=1)
    git_auto_commit: bool = False
    backup_original: bool = True
    create_branch: bool = True
    sessions_dir: str = "data/refactor_logs/sessions"
    snapshots_dir: str = "data/snapshots"
    logs_dir: str = "data/refactor_logs"
    storage_backend: str = Field(default="file", pattern=r"^(file|sqlite)$")

    def __init__(self, **data: Any) -> None:
        """Wraps pydantic's init to translate errors for backward compat."""
        try:
            super().__init__(**data)
        except ValidationError as exc:
            for err in exc.errors():
                if err["type"] == "extra_forbidden":
                    field = err["loc"][0] if err["loc"] else "unknown"
                    raise TypeError(
                        f"__init__() got an unexpected keyword argument '{field}'"
                    ) from None
            raise ValueError(str(exc)) from None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Priority: init kwargs > env vars > .env file > YAML > defaults."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            _YamlSettingsSource(settings_cls),
            file_secret_settings,
        )


# backward compat alias
Config = SNREConfig
