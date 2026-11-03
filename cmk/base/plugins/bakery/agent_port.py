#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from .bakery_api.v1 import (
    register,
    WindowsConfigGenerator,
    WindowsGlobalConfigEntry,
)


def get_agent_port_windows_config(conf: Mapping[str, int]) -> WindowsConfigGenerator:
    yield WindowsGlobalConfigEntry(name="port", content=conf["port"])


register.bakery_plugin(
    name="agent_port",
    windows_config_function=get_agent_port_windows_config,
)
