#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from typing import NotRequired, TypedDict
from urllib.parse import unquote

__all__ = [
    "ensure_mrpe_configs",
    "MrpeConfig",
    "MrpeConfigDeprecated",
]


# 2.2+ format: proper/actual
class MrpeConfig(TypedDict):
    description: str
    cmdline: str
    interval: NotRequired[int]


class _AsyncConfig(TypedDict):
    max_age: int
    appendage: bool


# 2.1 format: deprecated/legacy
MrpeConfigDeprecated = tuple[str, str, _AsyncConfig | None]


MrpeConfigs = Iterable[MrpeConfig | MrpeConfigDeprecated]


def ensure_mrpe_configs(configs: MrpeConfigs) -> Sequence[MrpeConfig]:
    """Converts legacy config to actual(proper) one"""
    return [
        _convert_to_proper_config(entry) if isinstance(entry, tuple) else entry for entry in configs
    ]


def _convert_to_proper_config(deprecated_entry: MrpeConfigDeprecated) -> MrpeConfig:
    migrated: MrpeConfig = {
        "description": unquote(deprecated_entry[0]),
        "cmdline": deprecated_entry[1],
    }
    if (async_config := deprecated_entry[2]) is not None:
        migrated["interval"] = async_config["max_age"]
    return migrated
