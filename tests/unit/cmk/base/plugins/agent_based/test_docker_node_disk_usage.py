#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

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


@pytest.mark.usefixtures("fix_register")
def test_check_docker_node_disk_usage() -> None:
    check = Check("docker_node_disk_usage")
    result = list(check.run_check("volumes", {}, check.run_parse(AGENT_OUTPUT)))
    assert result == [
        (0, "Size: 230 KiB", [("size", 235177, None, None)]),
        (0, "Reclaimable: 93 B", [("reclaimable", 93, None, None)]),
        (0, "Count: 7", [("count", 7, None, None)]),
        (0, "Active: 5", [("active", 5, None, None)]),
    ]
