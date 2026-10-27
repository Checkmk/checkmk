#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.bakery.v2 import OS, Plugin
from cmk.plugins.db2.bakery.mk_db2 import bakery_plugin_mk_db2
from tests.testlib.unit.bakelet_testing import APIBakeletTestSet, run_v2_bakelet_test

PLUGIN_NAME = "mk_db2"

TEST_SETS: dict[str, APIBakeletTestSet] = {
    "default": APIBakeletTestSet(
        conf={"deployment": ("cached", 100.0)},
        files=[
            Plugin(
                base_os=OS.LINUX,
                source=Path("mk_db2.linux"),
                target=Path("mk_db2"),
                interval=100,
            ),
            Plugin(
                base_os=OS.AIX,
                source=Path("mk_db2.aix"),
                target=Path("mk_db2"),
                interval=100,
            ),
        ],
    ),
    "do_not_deploy": APIBakeletTestSet(
        conf={"deployment": ("do_not_deploy", None)},
        files=[],
    ),
}


@pytest.mark.parametrize("test_name", TEST_SETS)
def test_mk_db2(
    test_name: str,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    run_v2_bakelet_test(bakery_plugin_mk_db2, TEST_SETS[test_name], mocker, tmp_path)
