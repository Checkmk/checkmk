#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.bakery.v2 import WindowsConfigEntry
from cmk.plugins.windows.bakery.logging import bakery_plugin_logging
from tests.testlib.unit.bakelet_testing import APIBakeletTestSet, run_v2_bakelet_test

PLUGIN_NAME = "logging"

TEST_SETS: dict[str, APIBakeletTestSet] = {
    "all": APIBakeletTestSet(
        conf={
            "logging_level": "yes",
            "max_log_file_count": 1,
            "max_log_file_size": 500001,
            "log_to_windbg": True,
        },
        windows_configs=[
            WindowsConfigEntry(
                path=["global", "logging", "debug"],
                content="yes",
            ),
            WindowsConfigEntry(
                path=["global", "logging", "max_file_count"],
                content=1,
            ),
            WindowsConfigEntry(
                path=["global", "logging", "max_file_size"],
                content=500001,
            ),
            WindowsConfigEntry(
                path=["global", "logging", "windbg"],
                content=True,
            ),
        ],
    ),
    "windbg_disabled": APIBakeletTestSet(
        conf={"log_to_windbg": False},
        windows_configs=[
            WindowsConfigEntry(
                path=["global", "logging", "windbg"],
                content=False,
            ),
        ],
    ),
    "logging_level_only": APIBakeletTestSet(
        conf={
            "logging_level": "all",
        },
        windows_configs=[
            WindowsConfigEntry(
                path=["global", "logging", "debug"],
                content="all",
            ),
        ],
    ),
}


@pytest.mark.parametrize("test_name", TEST_SETS)
def test_logging(
    test_name: str,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    run_v2_bakelet_test(bakery_plugin_logging, TEST_SETS[test_name], mocker, tmp_path)
