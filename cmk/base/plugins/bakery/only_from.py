#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from .bakery_api.v1 import (
    register,
    WindowsConfigGenerator,
    WindowsGlobalConfigEntry,
)


def get_only_from_windows_config(conf: Mapping[str, Sequence[str]]) -> WindowsConfigGenerator:
    yield WindowsGlobalConfigEntry(name="only_from", content=list(conf["allowed_addresses"]))


register.bakery_plugin(
    name="only_from",
    windows_config_function=get_only_from_windows_config,
)
