#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final

import pytest
from pytest_mock import MockerFixture

from cmk.bakery.v2 import WindowsConfigEntry
from cmk.plugins.generic_agent_options.bakery.agent_controller import bakery_plugin_agent_controller
from tests.testlib.unit.bakelet_testing import APIBakeletTestSet, run_v2_bakelet_test

_PLUGIN_NAME: Final = "agent_controller"


def _controller_path(entry: str) -> list[str]:
    return ["system", "controller", entry]


TEST_SETS: dict[str, APIBakeletTestSet] = {
    "enable": APIBakeletTestSet(
        conf={
            "agent_ctl_enabled": ("enabled", {}),
        },
        windows_configs=[
            WindowsConfigEntry(path=_controller_path("run"), content=True),
        ],
    ),
    "enable_with_runtime_opts": APIBakeletTestSet(
        conf={
            "agent_ctl_enabled": (
                "enabled",
                {
                    "detect_proxy": True,
                    "validate_api_cert": True,
                },
            ),
        },
        windows_configs=[
            WindowsConfigEntry(path=_controller_path("run"), content=True),
            WindowsConfigEntry(path=_controller_path("detect_proxy"), content=True),
            WindowsConfigEntry(path=_controller_path("validate_api_cert"), content=True),
        ],
    ),
    "disable": APIBakeletTestSet(
        conf={
            "agent_ctl_enabled": ("disabled", None),
        },
        windows_configs=[
            WindowsConfigEntry(path=_controller_path("run"), content=False),
        ],
    ),
    "absent": APIBakeletTestSet(
        conf={},
        windows_configs=[
            WindowsConfigEntry(path=_controller_path("run"), content=True),
        ],
    ),
}


@pytest.mark.parametrize("test_name", TEST_SETS)
def test_agent_controller(
    test_name: str,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    run_v2_bakelet_test(bakery_plugin_agent_controller, TEST_SETS[test_name], mocker, tmp_path)
