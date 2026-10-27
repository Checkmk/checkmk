#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.bakery.v2 import OS, PluginConfig
from cmk.plugins.collection.bakery.agent_exclude_sections import (
    bakery_plugin_agent_exclude_sections,
)
from tests.testlib.unit.bakelet_testing import APIBakeletTestSet, run_v2_bakelet_test

PLUGIN_NAME = "agent_exclude_sections"

config_lines = [
    "MK_SKIP_DF=yes",
    "MK_SKIP_SYSTEMD=yes",
    "MK_SKIP_ZFS=yes",
    "MK_SKIP_NFS_MOUNTS=yes",
]

TEST_SETS: dict[str, APIBakeletTestSet] = {
    "default": APIBakeletTestSet(
        conf={
            "sections": [
                "df",
                "systemd",
                "zfs",
                "nfs_mounts",
            ],
        },
        files=[
            PluginConfig(
                base_os=OS.LINUX,
                lines=config_lines,
                target=Path("exclude_sections.cfg"),
                include_header=True,
            ),
        ],
    ),
    "no_sections": APIBakeletTestSet(
        conf={},
        files=[],
    ),
}


@pytest.mark.parametrize("test_name", TEST_SETS)
def test_agent_exclude_sections(
    test_name: str,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    run_v2_bakelet_test(
        bakery_plugin_agent_exclude_sections,
        TEST_SETS[test_name],
        mocker,
        tmp_path,
    )
