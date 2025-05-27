#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper for standalone command line tool"""

from pathlib import Path

from ._parts import PathConfig
from ._type_defs import PackageError

_DEFAULT_PATH = Path("mkp-tool.toml")


def read_path_config(cfg_file: Path = _DEFAULT_PATH) -> PathConfig:
    """Read a toml configration file"""
    try:
        return PathConfig.from_toml(cfg_file.read_text(encoding="utf8"))
    except FileNotFoundError as exc:
        raise PackageError(f"Missing configuration file: {cfg_file}") from exc


def simple_file_write(file: Path, content: bytes) -> None:
    file.write_bytes(content)
