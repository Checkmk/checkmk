#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.bakery.v2 import OS, SystemBinary
from cmk.ccc.exceptions import MKGeneralException
from cmk.plugins.collection.bakery.win_openhardwaremonitor import (
    bakery_plugin_win_openhardwaremonitor,
    get_win_openhardwaremonitor_files,
)

CONFIG = {"deployment": ("sync", None)}
CONFIG_DO_NOT_DEPLOY = {"deployment": ("do_not_deploy", None)}


def test_win_openhardwaremonitor_do_not_deploy() -> None:
    assert (
        list(
            get_win_openhardwaremonitor_files(
                bakery_plugin_win_openhardwaremonitor.parameter_parser(CONFIG_DO_NOT_DEPLOY)
            )
        )
        == []
    )


def test_win_openhardwaremonitor_files_missing_raises() -> None:
    with (
        patch(
            "cmk.plugins.collection.bakery.win_openhardwaremonitor.os.path.exists",
            return_value=False,
        ),
        pytest.raises(MKGeneralException, match="OpenHardwareMonitor files are missing"),
    ):
        list(
            get_win_openhardwaremonitor_files(
                bakery_plugin_win_openhardwaremonitor.parameter_parser(CONFIG)
            )
        )


def test_win_openhardwaremonitor_files_dll_missing_raises() -> None:
    def fake_exists(path: str) -> bool:
        return "CLI.exe" in path

    with (
        patch(
            "cmk.plugins.collection.bakery.win_openhardwaremonitor.os.path.exists",
            side_effect=fake_exists,
        ),
        pytest.raises(MKGeneralException, match="OpenHardwareMonitor files are missing"),
    ):
        list(
            get_win_openhardwaremonitor_files(
                bakery_plugin_win_openhardwaremonitor.parameter_parser(CONFIG)
            )
        )


def test_win_openhardwaremonitor_files_success() -> None:
    with patch(
        "cmk.plugins.collection.bakery.win_openhardwaremonitor.os.path.exists", return_value=True
    ):
        result = list(
            get_win_openhardwaremonitor_files(
                bakery_plugin_win_openhardwaremonitor.parameter_parser(CONFIG)
            )
        )
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
