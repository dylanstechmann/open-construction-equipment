# SPDX-License-Identifier: Apache-2.0
"""Locate source checkout data or wheel-installed shared runtime resources."""

from __future__ import annotations

from pathlib import Path
import sys

from .config import ConfigError

_SOURCE_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIRECTORY = Path("share/open-construction-equipment")


def is_source_repository(path: Path) -> bool:
    return (path / "pyproject.toml").is_file() and (path / "schemas").is_dir()


def default_data_root() -> Path:
    if is_source_repository(_SOURCE_ROOT):
        return _SOURCE_ROOT
    installed = Path(sys.prefix) / _DATA_DIRECTORY
    if installed.is_dir():
        return installed
    raise ConfigError(f"OCE runtime data not found; expected source checkout or installed {installed}")
