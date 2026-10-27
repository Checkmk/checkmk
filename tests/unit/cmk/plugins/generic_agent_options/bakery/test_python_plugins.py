#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.bakery.v2 import OS, PluginConfig
from cmk.plugins.generic_agent_options.bakery.python_plugins import bakery_plugin_python_plugins
from tests.testlib.unit.bakelet_testing import APIBakeletTestSet, run_v2_bakelet_test

PLUGIN_NAME = "python_plugins"

TEST_SETS: dict[str, APIBakeletTestSet] = {
    "python2": APIBakeletTestSet(
        conf={
            "python_version": "python2",
        },
        files=[
            PluginConfig(
                base_os=OS.LINUX,
                lines=["PYTHON3="],
                target=Path("python_path.cfg"),
                include_header=True,
            ),
            PluginConfig(
                base_os=OS.AIX,
                lines=["PYTHON3="],
                target=Path("python_path.cfg"),
                include_header=True,
            ),
            PluginConfig(
                base_os=OS.SOLARIS,
                lines=["PYTHON3="],
                target=Path("python_path.cfg"),
                include_header=True,
            ),
        ],
    ),
    "custom_command": APIBakeletTestSet(
        conf={
            "python_version": "auto",
            "command": "paiton",
        },
        files=[
            PluginConfig(
                base_os=OS.LINUX,
                lines=[
                    "PYTHON2=paiton",
                    "PYTHON3=paiton",
                ],
                target=Path("python_path.cfg"),
                include_header=True,
            ),
            PluginConfig(
                base_os=OS.AIX,
                lines=[
                    "PYTHON2=paiton",
                    "PYTHON3=paiton",
                ],
                target=Path("python_path.cfg"),
                include_header=True,
            ),
            PluginConfig(
                base_os=OS.SOLARIS,
                lines=[
                    "PYTHON2=paiton",
                    "PYTHON3=paiton",
                ],
                target=Path("python_path.cfg"),
                include_header=True,
            ),
        ],
    ),
    "python3_w_command": APIBakeletTestSet(
        conf={
            "python_version": "python3",
            "command": "puehton",
        },
        files=[
            PluginConfig(
                base_os=OS.LINUX,
                lines=["PYTHON3=puehton", "PYTHON2="],
                target=Path("python_path.cfg"),
                include_header=True,
            ),
            PluginConfig(
                base_os=OS.AIX,
                lines=["PYTHON3=puehton", "PYTHON2="],
                target=Path("python_path.cfg"),
                include_header=True,
            ),
            PluginConfig(
                base_os=OS.SOLARIS,
                lines=["PYTHON3=puehton", "PYTHON2="],
                target=Path("python_path.cfg"),
                include_header=True,
            ),
        ],
    ),
}


@pytest.mark.parametrize("test_name", TEST_SETS)
def test_python_plugins(
    test_name: str,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    run_v2_bakelet_test(bakery_plugin_python_plugins, TEST_SETS[test_name], mocker, tmp_path)
