#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.bakery.v2 import OS, PluginConfig
from cmk.plugins.aix.bakery.exclude_sections_aix import bakery_plugin_exclude_sections_aix
from tests.testlib.unit.bakelet_testing import APIBakeletTestSet, run_v2_bakelet_test

PLUGIN_NAME = "exclude_sections_aix"

config_lines = [
    "MK_SKIP_CHECKMK_AGENT_PLUGINS=yes",
    "MK_SKIP_AIX_LPARSTAT=yes",
    "MK_SKIP_AIX_PAGING=yes",
    "MK_SKIP_MULTIPATHING=yes",
]

TEST_SETS: dict[str, APIBakeletTestSet] = {
    "default": APIBakeletTestSet(
        conf={
            "sections_aix": [
                "checkmk_agent_plugins",
                "aix_lparstat",
                "aix_paging",
                "multipathing",
            ]
        },
        files=[
            PluginConfig(
                base_os=OS.AIX,
                lines=config_lines,
                target=Path("exclude_sections_aix.cfg"),
                include_header=True,
            ),
        ],
    ),
}


@pytest.mark.parametrize("test_name", TEST_SETS)
def test_exclude_sections_aix(
    test_name: str,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    run_v2_bakelet_test(
        bakery_plugin_exclude_sections_aix,
        TEST_SETS[test_name],
        mocker,
        tmp_path,
    )
