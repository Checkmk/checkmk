#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pydantic import ValidationError

from cmk.werks.tool.config import (
    load_config,
    RuntimeConfiguration,
    try_load_current_version_from_defines_make,
)

_CONFIG = """
editions = [("community", "Community")]
components = [("core", "Core")]
edition_components = {"pro": [("cmc", "CMC")]}
classes = [("fix", "Bug fix", "FIX")]
levels = [("1", "Trivial change")]
compatible = [("yes", "Compatible"), ("no", "Incompatible")]
online_url = "https://checkmk.com/werk/%d"
"""


def _write_config(tmp_path: Path, extra: str = "") -> Path:
    config = tmp_path / "config"
    config.write_text(_CONFIG + extra, encoding="utf-8")
    return config


def _write_defines_make(tmp_path: Path, content: str) -> Path:
    defines_make = tmp_path / "defines.make"
    defines_make.write_text(content, encoding="utf-8")
    return defines_make


def test_the_current_version_of_the_config_file_wins(tmp_path: Path) -> None:
    config = _write_config(tmp_path, 'current_version = "2.4.0"\n')

    assert load_config(config, current_version="2.5.0").current_version == "2.4.0"


def test_the_current_version_falls_back_to_the_given_one(tmp_path: Path) -> None:
    config = _write_config(tmp_path)

    assert load_config(config, current_version="2.5.0").current_version == "2.5.0"


def test_a_config_without_any_current_version_is_rejected(tmp_path: Path) -> None:
    config = _write_config(tmp_path)

    with pytest.raises(ValidationError, match="current_version must be provided"):
        load_config(config)


def test_all_components_include_the_edition_specific_ones(tmp_path: Path) -> None:
    config = load_config(_write_config(tmp_path), current_version="2.5.0")

    assert config.all_components() == [("core", "Core"), ("cmc", "CMC")]


def test_the_version_is_read_from_defines_make(tmp_path: Path) -> None:
    defines_make = _write_defines_make(tmp_path, "EDITION := community\nVERSION := 2.5.0b1\n")

    assert try_load_current_version_from_defines_make(defines_make) == "2.5.0b1"


def test_defines_make_without_a_version_yields_none(tmp_path: Path) -> None:
    defines_make = _write_defines_make(tmp_path, "EDITION := community\n")

    assert try_load_current_version_from_defines_make(defines_make) is None


def test_a_missing_defines_make_yields_none(tmp_path: Path) -> None:
    assert try_load_current_version_from_defines_make(tmp_path / "defines.make") is None


def test_the_runtime_configuration_reads_the_version_of_the_repository(tmp_path: Path) -> None:
    _write_defines_make(tmp_path, "VERSION := 2.5.0\n")

    assert RuntimeConfiguration(tmp_path).get_defines_make_version() == "2.5.0"


def test_the_runtime_configuration_fails_without_a_version(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Could not load version from defines.make"):
        RuntimeConfiguration(tmp_path).get_defines_make_version()
