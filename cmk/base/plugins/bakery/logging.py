#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from typing import Literal

from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, WindowsConfigEntry


class _Config(BaseModel):
    logging_level: Literal["no", "yes", "all"] | None = None
    max_log_file_count: int | None = None
    max_log_file_size: int | None = None
    log_to_windbg: bool | None = None


def get_logging_windows_config(config: _Config) -> Iterator[WindowsConfigEntry]:
    if config.logging_level is not None:
        yield WindowsConfigEntry(path=["global", "logging", "debug"], content=config.logging_level)
    if config.max_log_file_count is not None:
        yield WindowsConfigEntry(
            path=["global", "logging", "max_file_count"], content=config.max_log_file_count
        )
    if config.max_log_file_size is not None:
        yield WindowsConfigEntry(
            path=["global", "logging", "max_file_size"], content=config.max_log_file_size
        )
    if config.log_to_windbg is not None:
        yield WindowsConfigEntry(path=["global", "logging", "windbg"], content=config.log_to_windbg)


bakery_plugin_logging = BakeryPlugin(
    name="logging",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    windows_config_function=get_logging_windows_config,
)
