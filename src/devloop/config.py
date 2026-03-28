from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import ValidationError

from devloop.models import Config


class ConfigError(RuntimeError):
    """Raised when config parsing or validation fails."""


def load_config(path: Path) -> Config:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in config file {path}: {exc}") from exc

    try:
        return Config.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"invalid config: {exc}") from exc
