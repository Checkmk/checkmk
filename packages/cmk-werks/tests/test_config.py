#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pydantic import ValidationError

from cmk.werks.tool.flavor_registry import load_config

_CONFIG = """
editions = [("community", "Community")]
components = [("core", "Core")]
edition_components = {"pro": [("cmc", "CMC")]}
classes = [("fix", "Bug fix", "FIX")]
levels = [("1", "Trivial change")]
compatible = [("yes", "Compatible"), ("no", "Incompatible")]
online_url = "https://checkmk.com/werk/%d"
"""


def _write_config(tmp_path: Path, extra: str = 'flavor = "cmk"\n') -> Path:
    config = tmp_path / "config"
    config.write_text(_CONFIG + extra, encoding="utf-8")
    return config


def _write_defines_make(tmp_path: Path) -> None:
    (tmp_path / "defines.make").write_text("VERSION := 2.5.0\n", encoding="utf-8")


def test_the_current_version_of_the_config_file_wins(tmp_path: Path) -> None:
    _write_defines_make(tmp_path)
    config = _write_config(tmp_path, 'flavor = "cmk"\ncurrent_version = "2.4.0"\n')

    assert load_config(config, tmp_path).current_version == "2.4.0"


def test_the_current_version_falls_back_to_the_one_of_the_repository(tmp_path: Path) -> None:
    _write_defines_make(tmp_path)

    assert load_config(_write_config(tmp_path), tmp_path).current_version == "2.5.0"


def test_a_config_without_any_current_version_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="current_version must be provided"):
        load_config(_write_config(tmp_path), tmp_path)


@pytest.mark.parametrize(
    "flavor",
    [pytest.param("", id="missing"), pytest.param('flavor = "unknown"\n', id="unknown")],
)
def test_a_config_needs_a_known_flavor(tmp_path: Path, flavor: str) -> None:
    _write_defines_make(tmp_path)

    with pytest.raises(ValueError, match="'flavor' has to be one of .*cmk"):
        load_config(_write_config(tmp_path, flavor), tmp_path)


def test_all_components_include_the_edition_specific_ones(tmp_path: Path) -> None:
    _write_defines_make(tmp_path)
    config = load_config(_write_config(tmp_path), tmp_path)

    assert config.all_components() == [("core", "Core"), ("cmc", "CMC")]


def test_a_legacy_edition_is_listed_as_its_current_name(tmp_path: Path) -> None:
    _write_defines_make(tmp_path)
    config = load_config(_write_config(tmp_path), tmp_path)

    assert config.canonical_edition("cee") == "pro"
