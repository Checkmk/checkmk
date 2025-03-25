#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.legacy_checks.docker_node_disk_usage import (
    check_docker_node_disk_usage,
    parse_docker_node_disk_usage,
)

AGENT_OUTPUT = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.4.2", "ApiVersion": "1.41"}',
    ],
    ['{"count": 5, "active": 5, "type": "images", "reclaimable": 0, "size": 325130565}'],
    ['{"count": 7, "active": 2, "type": "containers", "reclaimable": 39196, "size": 39196}'],
    ['{"count": 7, "active": 5, "type": "volumes", "reclaimable": 93, "size": 235177}'],
    ['{"count": 0, "active": 0, "type": "buildcache", "reclaimable": 0, "size": 0}'],
]


@pytest.mark.usefixtures("agent_based_plugins")
def test_check_docker_node_disk_usage() -> None:
    result = list(
        check_docker_node_disk_usage("volumes", {}, parse_docker_node_disk_usage(AGENT_OUTPUT))
    )
    assert result == [
        (0, "Size: 230 KiB", [("size", 235177, None, None)]),
        (0, "Reclaimable: 93 B", [("reclaimable", 93, None, None)]),
        (0, "Count: 7", [("count", 7, None, None)]),
        (0, "Active: 5", [("active", 5, None, None)]),
    ]
