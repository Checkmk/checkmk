#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]
from cmk.base.check_api import MKCounterWrapped
from checktestlib import (
    DiscoveryResult,
    assertDiscoveryResultsEqual,
    MockItemState,
)

pytestmark = pytest.mark.checks


INFO_MISSING_COUNTERS = [
    ['@docker_version_info', '{"PluginVersion": "0.1", "DockerPyVersion": "3.7.0", "ApiVersion": "1.38"}'],
    ['{"io_service_time_recursive": [], "sectors_recursive": [], "io_service_bytes_recursive": [], "io_serviced_recursive": [], "io_time_recursive": [], "names"    : {"7:9": "loop9", "8:0": "sda", "7:8": "loop8", "8:16": "sdb", "253:1": "dm-1", "253:0": "dm-0", "7:4": "loop4", "253:2": "dm-2", "7:2": "loop2", "7:3":     "loop3", "7:0": "loop0", "7:1": "loop1", "7:10": "loop10", "7:6": "loop6", "7:12": "loop12", "7:13": "loop13", "7:7": "loop7", "8:32": "sdc", "7:5": "loop    5", "7:11": "loop11"}, "time": 1568705427.380945, "io_queue_recursive": [], "io_merged_recursive": [], "io_wait_time_recursive": []}'],
]


@pytest.mark.usefixtures("config_load_all_checks")
def test_docker_container_diskstat_wrapped():
    check = Check('docker_container_diskstat')
    parsed = check.run_parse(INFO_MISSING_COUNTERS)

    with pytest.raises(MKCounterWrapped):
        check.run_check("SUMMARY", {}, parsed)

    with MockItemState((0, 0)):
        # raise MKCounterWrapped anyway, because counters are missing in info
        with pytest.raises(MKCounterWrapped):
            check.run_check("SUMMARY", {}, parsed)


@pytest.mark.parametrize("info, discovery_expected", [
    (INFO_MISSING_COUNTERS, DiscoveryResult([("SUMMARY", {})])),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_docker_container_diskstat_discovery(info, discovery_expected):
    check = Check('docker_container_diskstat')
    parsed = check.run_parse(info)
    discovery_actual = DiscoveryResult(check.run_discovery(parsed))
    assertDiscoveryResultsEqual(check, discovery_actual, discovery_expected)
