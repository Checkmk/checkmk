#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pydantic import BaseModel

from cmk.bakery.v2 import BakeryPlugin, WindowsConfigEntry, WindowsConfigGenerator


class _Config(BaseModel):
    installation: str = "auto"
    usage: str = "auto"


# modules:
#   enabled: yes
#   python: system # or nothing or auto
def get_agent_install_python_config(config: _Config) -> WindowsConfigGenerator:
    yield WindowsConfigEntry(path=["modules", "python"], content=config.usage)


bakery_plugin_install_python = BakeryPlugin(
    name="install_python",
    parameter_parser=_Config.model_validate,
    default_parameters=None,
    windows_config_function=get_agent_install_python_config,
)
