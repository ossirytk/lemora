"""Configuration handling for lemora."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_dir


@dataclass(slots=True, frozen=True)
class LemoraConfig:
    """Runtime paths and optional model settings."""

    data_dir: Path
    whitaker_path: Path | None
    lewis_short_path: Path | None
    model_path: Path | None

    @classmethod
    def from_env(cls) -> LemoraConfig:
        """Build config from environment variables."""
        data_dir = Path(
            os.getenv("LEMORA_DATA_DIR", user_data_dir(appname="lemora", appauthor=False)),
        )
        whitaker_path = _optional_path("LEMORA_WHITAKER_PATH")
        lewis_short_path = _optional_path("LEMORA_LEWIS_SHORT_PATH")
        model_path = _optional_path("LEMORA_MODEL_PATH")
        return cls(
            data_dir=data_dir,
            whitaker_path=whitaker_path,
            lewis_short_path=lewis_short_path,
            model_path=model_path,
        )


def _optional_path(env_name: str) -> Path | None:
    raw_value = os.getenv(env_name)
    if raw_value is None or raw_value.strip() == "":
        return None
    return Path(raw_value).expanduser()
