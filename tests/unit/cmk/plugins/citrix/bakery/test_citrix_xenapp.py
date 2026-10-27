#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.bakery.v2 import OS, Plugin
from cmk.plugins.citrix.bakery.citrix_xenapp import bakery_plugin_citrix_xenapp
from tests.testlib.unit.bakelet_testing import APIBakeletTestSet, run_v2_bakelet_test

PLUGIN_NAME = "citrix_xenapp"

CONFIG = {"deployment": ("sync", None)}


TEST_SETS: dict[str, APIBakeletTestSet] = {
    "default": APIBakeletTestSet(
        conf=CONFIG,
        files=[
            Plugin(base_os=OS.WINDOWS, source=Path("citrix_xenapp.ps1")),
        ],
    ),
}


@pytest.mark.parametrize("test_name", TEST_SETS)
def test_citrix_xenapp(
    test_name: str,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    run_v2_bakelet_test(bakery_plugin_citrix_xenapp, TEST_SETS[test_name], mocker, tmp_path)
