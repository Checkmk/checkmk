#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import quote

from cmk.utils.mrpe_config import MrpeConfig

from .bakery_api.v1 import (
    FileGenerator,
    OS,
    PluginConfig,
    register,
    WindowsConfigGenerator,
    WindowsConfigItems,
)


def get_mrpe_files(conf: Sequence[Sequence[MrpeConfig]]) -> FileGenerator:
    lines = [_formatted_mrpe_line(mrpe_config) for mrpe_config in _merge_rule_values(conf)]
    for o_s in [OS.LINUX, OS.SOLARIS, OS.AIX]:
        yield PluginConfig(
            base_os=o_s,
            lines=lines,
            target=Path("mrpe.cfg"),
            include_header=True,
        )


def get_mrpe_windows_config(conf: Sequence[Sequence[MrpeConfig]]) -> WindowsConfigGenerator:
    if not (mrpe_configs := _merge_rule_values(conf)):
        return  # section should not be created if list is empty

    yield WindowsConfigItems(
        path=["mrpe", "config"],
        content=[f"check = {_formatted_mrpe_line(mrpe_config)}" for mrpe_config in mrpe_configs],
    )


def _merge_rule_values(conf: Sequence[Sequence[MrpeConfig]]) -> list[MrpeConfig]:
    return [mrpe_config for rule_value in conf for mrpe_config in rule_value]


def _formatted_mrpe_line(mrpe_config: MrpeConfig) -> str:
    quoted_description = _quote(mrpe_config["description"])
    interval_spec = f" (interval={mrpe_config['interval']}) " if "interval" in mrpe_config else " "
    return f"{quoted_description}{interval_spec}{mrpe_config['cmdline']}"


def _quote(service_description: str) -> str:
    """Ensure that cache file names are almost POSIX-conform (except for '%')"""
    return quote(
        service_description,
        safe="",
    )


register.bakery_plugin(
    name="mrpe",
    files_function=get_mrpe_files,
    windows_config_function=get_mrpe_windows_config,
)
