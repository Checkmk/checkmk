#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.bakery.v1 import OS, SystemBinary
from cmk.base.plugins.bakery.win_openhardwaremonitor import (
    get_win_openhardwaremonitor_files,
)
from cmk.ccc.exceptions import MKGeneralException

CONFIG = {"deployment": ("sync", None)}
CONFIG_DO_NOT_DEPLOY = {"deployment": ("do_not_deploy", None)}


def test_win_openhardwaremonitor_do_not_deploy() -> None:
    assert list(get_win_openhardwaremonitor_files(CONFIG_DO_NOT_DEPLOY)) == []


def test_win_openhardwaremonitor_files_missing_raises() -> None:
    with patch(
        "cmk.base.plugins.bakery.win_openhardwaremonitor.os.path.exists", return_value=False
    ):
        with pytest.raises(MKGeneralException, match="OpenHardwareMonitor files are missing"):
            list(get_win_openhardwaremonitor_files(CONFIG))


def test_win_openhardwaremonitor_files_dll_missing_raises() -> None:
    def fake_exists(path: str) -> bool:
        return "CLI.exe" in path

    with patch(
        "cmk.base.plugins.bakery.win_openhardwaremonitor.os.path.exists", side_effect=fake_exists
    ):
        with pytest.raises(MKGeneralException, match="OpenHardwareMonitor files are missing"):
            list(get_win_openhardwaremonitor_files(CONFIG))


def test_win_openhardwaremonitor_files_success() -> None:
    with patch("cmk.base.plugins.bakery.win_openhardwaremonitor.os.path.exists", return_value=True):
        result = list(get_win_openhardwaremonitor_files(CONFIG))
    assert result == [
        SystemBinary(
            base_os=OS.WINDOWS,
            source=Path("OpenHardwareMonitorCLI.exe"),
            target=Path("OpenHardwareMonitorCLI.exe"),
        ),
        SystemBinary(
            base_os=OS.WINDOWS,
            source=Path("OpenHardwareMonitorLib.dll"),
            target=Path("OpenHardwareMonitorLib.dll"),
        ),
    ]
