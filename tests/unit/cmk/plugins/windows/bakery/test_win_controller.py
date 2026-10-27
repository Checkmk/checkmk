#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final

import pytest
from pytest_mock import MockerFixture

from cmk.bakery.v2 import WindowsConfigEntry
from cmk.plugins.windows.bakery.win_controller import _path_to, bakery_plugin_win_controller
from tests.testlib.unit.bakelet_testing import APIBakeletTestSet, run_v2_bakelet_test

_PLUGIN_NAME: Final = "win_controller"

TEST_SETS: dict[str, APIBakeletTestSet] = {
    "enable": APIBakeletTestSet(
        conf={
            "check_access": True,
            "allow_legacy": False,
        },
        windows_configs=[
            WindowsConfigEntry(path=_path_to("check"), content=True),
            WindowsConfigEntry(path=_path_to("force_legacy"), content=False),
        ],
    ),
    "non-default-config": APIBakeletTestSet(
        conf={
            "check_access": False,
            "allow_legacy": True,
        },
        windows_configs=[
            WindowsConfigEntry(path=_path_to("check"), content=False),
            WindowsConfigEntry(path=_path_to("force_legacy"), content=True),
        ],
    ),
    "agent-channel-mailslot": APIBakeletTestSet(
        conf={
            "check_access": True,
            "allow_legacy": False,
            "agent_channel": ("mailslot", None),
        },
        windows_configs=[
            WindowsConfigEntry(path=_path_to("check"), content=True),
            WindowsConfigEntry(path=_path_to("force_legacy"), content=False),
            WindowsConfigEntry(path=_path_to("agent_channel"), content="mailslot"),
        ],
    ),
    "agent-channel-tcp": APIBakeletTestSet(
        conf={
            "check_access": True,
            "allow_legacy": False,
            "agent_channel": ("tcp", 28250),
        },
        windows_configs=[
            WindowsConfigEntry(path=_path_to("check"), content=True),
            WindowsConfigEntry(path=_path_to("force_legacy"), content=False),
            WindowsConfigEntry(path=_path_to("agent_channel"), content="localhost:28250"),
        ],
    ),
}


@pytest.mark.parametrize("test_name", TEST_SETS)
def test_win_controller(
    test_name: str,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    run_v2_bakelet_test(bakery_plugin_win_controller, TEST_SETS[test_name], mocker, tmp_path)
