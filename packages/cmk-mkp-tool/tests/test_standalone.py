#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.mkp_tool import PackageError, PathConfig
from cmk.mkp_tool._parts import make_path_config_template
from cmk.mkp_tool._standalone import read_path_config, simple_file_write


def test_read_path_config_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "nope.toml"

    with pytest.raises(PackageError, match="Missing configuration file"):
        _ = read_path_config(missing)


def test_read_path_config_roundtrip(tmp_path: Path) -> None:
    template = make_path_config_template()
    cfg_file = tmp_path / "mkp-tool.toml"
    cfg_file.write_text(template.to_toml(), encoding="utf8")

    assert read_path_config(cfg_file) == template


def test_read_path_config_reads_actual_values(tmp_path: Path, path_config: PathConfig) -> None:
    cfg_file = tmp_path / "mkp-tool.toml"
    cfg_file.write_text(path_config.to_toml(), encoding="utf8")

    assert read_path_config(cfg_file) == path_config


def test_simple_file_write(tmp_path: Path) -> None:
    target = tmp_path / "some-file"

    simple_file_write(target, b"\x00binary content")

    assert target.read_bytes() == b"\x00binary content"


def test_simple_file_write_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "some-file"
    target.write_bytes(b"old")

    simple_file_write(target, b"new")

    assert target.read_bytes() == b"new"
