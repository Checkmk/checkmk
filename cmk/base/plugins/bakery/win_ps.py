#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from .bakery_api.v1 import register, WindowsConfigEntry, WindowsConfigGenerator


def get_win_ps_windows_config(conf: Mapping[str, bool]) -> WindowsConfigGenerator:
    use_wmi = conf.get("use_wmi", False)
    yield WindowsConfigEntry(path=["ps", "use_wmi"], content=use_wmi is True)

    if not use_wmi:
        return

    if conf.get("full_path", False):
        yield WindowsConfigEntry(path=["ps", "full_path"], content=True)


register.bakery_plugin(
    name="win_ps",
    windows_config_function=get_win_ps_windows_config,
)
