#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.legacy_checks.docker_node_disk_usage import (
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


def test_check_docker_node_disk_usage() -> None:
    result = list(
        check_docker_node_disk_usage("volumes", {}, parse_docker_node_disk_usage(AGENT_OUTPUT))
    )
    assert result == [
        Result(state=State.OK, summary="Size: 230 KiB"),
        Metric("size", 235177.0),
        Result(state=State.OK, summary="Reclaimable: 93 B"),
        Metric("reclaimable", 93.0),
        Result(state=State.OK, summary="Count: 7"),
        Metric("count", 7.0),
        Result(state=State.OK, summary="Active: 5"),
        Metric("active", 5.0),
    ]
