#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.bakery.v2 import OS, Plugin, PluginConfig
from cmk.plugins.docker.bakery.mk_docker import bakery_plugin_mk_docker
from tests.testlib.unit.bakelet_testing import APIBakeletTestSet, run_v2_bakelet_test

PLUGIN_NAME = "mk_docker"

CONFIG = {
    "deployment": ("cached", 3000.0),
    "node": [],
    "container_id": "long",
    "base_url": "unix://var/run/docker.sock",
    "containers": [
        "docker_container_labels",
        "docker_container_mem",
        "docker_container_cpu",
    ],
}

CONFIG_LINES = [
    "[DOCKER]",
    "skip_sections: docker_container_labels,docker_container_mem,docker_container_cpu",
    "container_id: long",
    "base_url: unix://var/run/docker.sock",
]

TEST_SETS: dict[str, APIBakeletTestSet] = {
    "default": APIBakeletTestSet(
        conf=CONFIG,
        files=[
            Plugin(base_os=OS.LINUX, source=Path("mk_docker.py"), interval=3000),
            PluginConfig(
                base_os=OS.LINUX,
                lines=CONFIG_LINES,
                target=Path("docker.cfg"),
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
def test_mk_docker(
    test_name: str,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    run_v2_bakelet_test(bakery_plugin_mk_docker, TEST_SETS[test_name], mocker, tmp_path)
