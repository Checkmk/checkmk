#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from cmk.ccc.exceptions import MKGeneralException
from cmk.utils.paths import local_agents_dir

from .bakery_api.v1 import FileGenerator, OS, register, SystemBinary


class _Config(BaseModel):
    deployment: tuple[Literal["do_not_deploy", "sync", "cached"], float | None]


def get_win_openhardwaremonitor_files(conf: Mapping[str, object]) -> FileGenerator:
    config = _Config.model_validate(conf)
    if config.deployment[0] == "do_not_deploy":
        return

    path_to_dll = os.path.join(local_agents_dir, "windows", "OpenHardwareMonitorLib.dll")
    path_to_exe = os.path.join(local_agents_dir, "windows", "OpenHardwareMonitorCLI.exe")
    if not os.path.exists(path_to_dll) or not os.path.exists(path_to_exe):
        raise MKGeneralException(
            "OpenHardwareMonitor files are missing due to security reasons, you may need to install it. Have a look at werk #18537 for further information.",
        )

    yield SystemBinary(
        base_os=OS.WINDOWS,
        source=Path("OpenHardwareMonitorCLI.exe"),
        target=Path("OpenHardwareMonitorCLI.exe"),
    )
    yield SystemBinary(
        base_os=OS.WINDOWS,
        source=Path("OpenHardwareMonitorLib.dll"),
        target=Path("OpenHardwareMonitorLib.dll"),
    )


register.bakery_plugin(
    name="win_openhardwaremonitor",
    files_function=get_win_openhardwaremonitor_files,
)
