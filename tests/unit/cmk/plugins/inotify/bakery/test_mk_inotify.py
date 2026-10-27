#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.bakery.v2 import OS, Plugin, PluginConfig
from cmk.plugins.inotify.bakery.mk_inotify import bakery_plugin_mk_inotify
from tests.testlib.unit.bakelet_testing import APIBakeletTestSet, run_v2_bakelet_test

PLUGIN_NAME = "mk_inotify"

CONFIG = {
    "deployment": ("sync", None),
    "heartbeat_timeout": 120.0,
    "write_interval": 10.0,
    "max_messages_per_interval": 100,
    "stats_retention": 120.0,
    "entries": [
        (
            "files",
            {"path": "some/path", "files": ["some", "files"], "operations": ["create", "open"]},
        ),
        ("folder", {"path": "other/path", "operations": ["delete"]}),
    ],
}

CONFIG_LINES = [
    "[global]",
    "heartbeat_timeout=120",
    "write_interval=10",
    "max_messages_per_interval=100",
    "stats_retention=120",
    "",
    "[some/path|some|files]",
    "create=1",
    "open=1",
    "[other/path]",
    "delete=1",
]


TEST_SETS: dict[str, APIBakeletTestSet] = {
    "default": APIBakeletTestSet(
        conf=CONFIG,
        files=[
            Plugin(base_os=OS.LINUX, source=Path("mk_inotify.py")),
            PluginConfig(
                base_os=OS.LINUX,
                lines=CONFIG_LINES,
                target=Path("mk_inotify.cfg"),
                include_header=True,
            ),
        ],
    ),
    "do_not_deploy": APIBakeletTestSet(
        conf={"deployment": ("do_not_deploy", None)},
        files=[],
    ),
}


@pytest.mark.parametrize("test_name", TEST_SETS)
def test_mk_inotify(
    test_name: str,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    run_v2_bakelet_test(bakery_plugin_mk_inotify, TEST_SETS[test_name], mocker, tmp_path)
