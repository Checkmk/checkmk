#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from typing import Any

from .bakery_api.v1 import register, WindowsConfigEntry, WindowsConfigGenerator


# will be called during generation of the final yml
def get_agent_install_python_config(conf: Any) -> WindowsConfigGenerator:
    if not conf:
        return  # TODO: For some obscure reason, we sometimes get False for conf...

    # ...expected yml...
    # modules:
    #   enabled: yes
    #   python: system # or nothing or auto
    # ..................
    yield WindowsConfigEntry(path=["modules", "python"], content=conf["usage"])


register.bakery_plugin(
    name="install_python",
    windows_config_function=get_agent_install_python_config,
)
