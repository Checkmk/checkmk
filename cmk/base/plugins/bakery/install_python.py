#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from pydantic import BaseModel

from .bakery_api.v1 import register, WindowsConfigEntry, WindowsConfigGenerator


class _Config(BaseModel):
    installation: str = "auto"
    usage: str = "auto"


# modules:
#   enabled: yes
#   python: system # or nothing or auto
def get_agent_install_python_config(conf: Mapping[str, object]) -> WindowsConfigGenerator:
    config = _Config.model_validate(conf)
    yield WindowsConfigEntry(path=["modules", "python"], content=config.usage)


register.bakery_plugin(
    name="install_python",
    windows_config_function=get_agent_install_python_config,
)
