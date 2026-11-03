#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

# registration
from .bakery_api.v1 import (
    FileGenerator,
    OS,
    PluginConfig,
    register,
    WindowsConfigEntry,
    WindowsConfigGenerator,
)


def get_fileinfo_files(conf: Sequence[Sequence[str]]) -> FileGenerator:
    patterns = _merge_rule_values(conf)
    for base_os in (OS.LINUX, OS.SOLARIS, OS.AIX):
        yield PluginConfig(base_os=base_os, lines=patterns, target=Path("fileinfo.cfg"))


def get_fileinfo_windows_config(conf: Sequence[Sequence[str]]) -> WindowsConfigGenerator:
    # TODO (au): Please, check the code here: We should NOT create fileinfo entry, if conf is empty
    # I ain't sure with all those yield/return in different combinations: win/lin, plugin/entry
    if not (patterns := _merge_rule_values(conf)):
        return

    yield WindowsConfigEntry(path=["fileinfo", "path"], content=patterns)


def _merge_rule_values(conf: Sequence[Sequence[str]]) -> list[str]:
    return [pattern for rule_value in conf for pattern in rule_value]


register.bakery_plugin(
    name="fileinfo",
    files_function=get_fileinfo_files,
    windows_config_function=get_fileinfo_windows_config,
)
