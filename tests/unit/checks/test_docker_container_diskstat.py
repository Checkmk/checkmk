#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]
from cmk.base.check_api import MKCounterWrapped
from cmk.utils.type_defs import CheckPluginName, SectionName
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_LEVELS
import cmk.base.api.agent_based.register as agent_based_register
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

CGROUP_V2 = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}'
    ],
    [
        '{"io_service_bytes_recursive": [{"major": 259, "minor": 0, "op": "read", "value": '
        '897024}, {"major": 259, "minor": 0, "op": "write", "value": 0}, {"major": 253, "mi'
        'nor": 0, "op": "read", "value": 897024}, {"major": 253, "minor": 0, "op": "write",'
        '"value": 0}, {"major": 253, "minor": 1, "op": "read", "value": 897024}, {"major": '
        '253, "minor": 1, "op": "write", "value": 0}], "io_serviced_recursive": null, "io_q'
        'ueue_recursive": null, "io_service_time_recursive": null, "io_wait_time_recursive"'
        ': null, "io_merged_recursive": null, "io_time_recursive": null, "sectors_recursive'
        '": null, "time": 1637679467.388989, "names": {"7:1": "loop1", "253:1": "dm-1", "25'
        '9:0": "nvme0n1", "7:8": "loop8", "7:15": "loop15", "7:6": "loop6", "7:13": "loop13'
        '", "7:4": "loop4", "7:11": "loop11", "7:2": "loop2", "253:2": "dm-2", "7:0": "loop'
        '0", "253:0": "dm-0", "7:9": "loop9", "7:7": "loop7", "8:0": "sda", "7:14": "loop14'
        '", "7:5": "loop5", "7:12": "loop12", "7:3": "loop3", "7:10": "loop10"}}'
    ]
]

CGROUP_V1 = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "ApiVersion": "1.39", "DockerPyVersion": "2.6.1"}'
    ],
    [
        '{"io_service_time_recursive": [{"major": 8, "op": "Read", "value": 17329675, "mino'
        'r": 0}, {"major": 8, "op": "Write", "value": 0, "minor": 0}, {"major": 8, "op": "S'
        'ync", "value": 0, "minor": 0}, {"major": 8, "op": "Async", "value": 17329675, "min'
        'or": 0}, {"major": 8, "op": "Total", "value": 17329675, "minor": 0}], "io_time_rec'
        'ursive": [{"major": 8, "op": "", "value": 40569604, "minor": 0}], "names": {"8:0":'
        '"sda", "11:0": "sr0"}, "io_serviced_recursive": [{"major": 8, "op": "Read", "value'
        '": 26, "minor": 0}, {"major": 8, "op": "Write", "value": 0, "minor": 0}, {"major":'
        '8, "op": "Sync", "value": 0, "minor": 0}, {"major": 8, "op": "Async", "value": 26,'
        '"minor": 0}, {"major": 8, "op": "Total", "value": 26, "minor": 0}, {"major": 8, "o'
        'p": "Read", "value": 26, "minor": 0}, {"major": 8, "op": "Write", "value": 0, "min'
        'or": 0}, {"major": 8, "op": "Sync", "value": 0, "minor": 0}, {"major": 8, "op": "A'
        'sync", "value": 26, "minor": 0}, {"major": 8, "op": "Total", "value": 26, "minor":'
        '0}], "io_queue_recursive": [{"major": 8, "op": "Read", "value": 0, "minor": 0}, {"'
        'major": 8, "op": "Write", "value": 0, "minor": 0}, {"major": 8, "op": "Sync", "val'
        'ue": 0, "minor": 0}, {"major": 8, "op": "Async", "value": 0, "minor": 0}, {"major"'
        ': 8, "op": "Total", "value": 0, "minor": 0}], "io_wait_time_recursive": [{"major":'
        '8, "op": "Read", "value": 369899, "minor": 0}, {"major": 8, "op": "Write", "value"'
        ': 0, "minor": 0}, {"major": 8, "op": "Sync", "value": 0, "minor": 0}, {"major": 8,'
        '"op": "Async", "value": 369899, "minor": 0}, {"major": 8, "op": "Total", "value": '
        '369899, "minor": 0}], "io_service_bytes_recursive": [{"major": 8, "op": "Read", "v'
        'alue": 1331200, "minor": 0}, {"major": 8, "op": "Write", "value": 0, "minor": 0}, '
        '{"major": 8, "op": "Sync", "value": 0, "minor": 0}, {"major": 8, "op": "Async", "v'
        'alue": 1331200, "minor": 0}, {"major": 8, "op": "Total", "value": 1331200, "minor"'
        ': 0}, {"major": 8, "op": "Read", "value": 1331200, "minor": 0}, {"major": 8, "op":'
        '"Write", "value": 0, "minor": 0}, {"major": 8, "op": "Sync", "value": 0, "minor": '
        '0}, {"major": 8, "op": "Async", "value": 1331200, "minor": 0}, {"major": 8, "op": '
        '"Total", "value": 1331200, "minor": 0}], "io_merged_recursive": [{"major": 8, "op"'
        ': "Read", "value": 0, "minor": 0}, {"major": 8, "op": "Write", "value": 0, "minor"'
        ': 0}, {"major": 8, "op": "Sync", "value": 0, "minor": 0}, {"major": 8, "op": "Asyn'
        'c", "value": 0, "minor": 0}, {"major": 8, "op": "Total", "value": 0, "minor": 0}],'
        '"time": 1637739081.5936825, "sectors_recursive": [{"major": 8, "op": "", "value": '
        '2600, "minor": 0}]}'
    ]
]

PLUGIN_OUTPUT_CGROUP_V2_0_SEC = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}',
    ],
    [
        '{"io_service_bytes_recursive": [{"major": 259, "minor": 0, "op": "read", "value": 1389854720'
        '}, {"major": 259, "minor": 0, "op": "write", "value": 0}, {"major": 253, "minor": 0, "op": "'
        'read", "value": 1389854720}, {"major": 253, "minor": 0, "op": "write", "value": 5438197760},'
        '{"major": 253, "minor": 1, "op": "read", "value": 1389854720}, {"major": 253, "minor": 1, "o'
        'p": "write", "value": 5438197760}], "io_serviced_recursive": null, "io_queue_recursive": nul'
        'l, "io_service_time_recursive": null, "io_wait_time_recursive": null, "io_merged_recursive":'
        'null, "io_time_recursive": null, "sectors_recursive": null, "time": 1637748634.5162437, "nam'
        'es": {"7:1": "loop1", "253:1": "dm-1", "259:0": "nvme0n1", "7:17": "loop17", "7:8": "loop8",'
        '"7:15": "loop15", "7:6": "loop6", "7:13": "loop13", "7:4": "loop4", "7:11": "loop11", "7:2":'
        '"loop2", "253:2": "dm-2", "7:0": "loop0", "253:0": "dm-0", "7:9": "loop9", "7:16": "loop16",'
        '"7:7": "loop7", "8:0": "sda", "7:14": "loop14", "7:5": "loop5", "7:12": "loop12", "7:3": "lo'
        'op3", "7:10": "loop10"}}'
    ],
]

PLUGIN_OUTPUT_CGROUP_V2_272_SEC = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}',
    ],
    [
        '{"io_service_bytes_recursive": [{"major": 259, "minor": 0, "op": "read", "value": 1583906816'
        '}, {"major": 259, "minor": 0, "op": "write", "value": 0}, {"major": 253, "minor": 0, "op": "'
        'read", "value": 1583906816}, {"major": 253, "minor": 0, "op": "write", "value": 8336506880},'
        '{"major": 253, "minor": 1, "op": "read", "value": 1583906816}, {"major": 253, "minor": 1, "o'
        'p": "write", "value": 8336506880}], "io_serviced_recursive": null, "io_queue_recursive": nul'
        'l, "io_service_time_recursive": null, "io_wait_time_recursive": null, "io_merged_recursive":'
        'null, "io_time_recursive": null, "sectors_recursive": null, "time": 1637748906.878384, "name'
        's": {"7:1": "loop1", "253:1": "dm-1", "259:0": "nvme0n1", "7:17": "loop17", "7:8": "loop8", '
        '"7:15": "loop15", "7:6": "loop6", "7:13": "loop13", "7:4": "loop4", "7:11": "loop11", "7:2":'
        '"loop2", "253:2": "dm-2", "7:0": "loop0", "253:0": "dm-0", "7:9": "loop9", "7:16": "loop16",'
        '"7:7": "loop7", "8:0": "sda", "7:14": "loop14", "7:5": "loop5", "7:12": "loop12", "7:3": "lo'
        'op3", "7:10": "loop10"}}'
    ],
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


@pytest.mark.parametrize("info, expected_parsed", [
    pytest.param(CGROUP_V1, {
        'sda': (1637739081.5936825, {
            'bytes': {
                'Async': 1331200,
                'Read': 1331200,
                'Sync': 0,
                'Total': 1331200,
                'Write': 0
            },
            'ios': {
                'Async': 26,
                'Read': 26,
                'Sync': 0,
                'Total': 26,
                'Write': 0
            },
            'name': 'sda'
        }),
        'sr0': (1637739081.5936825, {
            'bytes': {},
            'ios': {},
            'name': 'sr0'
        }),
    },
                 id="cgroup v1"),
    pytest.param(CGROUP_V2, {
        'dm-0': (1637679467.388989, {
            'bytes': {'read': 897024, 'write': 0},
            'ios': {},
            'name': 'dm-0'
        }),
        'dm-1': (1637679467.388989, {
            'bytes': {'read': 897024, 'write': 0},
            'ios': {},
            'name': 'dm-1'
        }),
        'dm-2': (1637679467.388989, {
            'bytes': {},
            'ios': {},
            'name': 'dm-2'
        }),
        'nvme0n1': (1637679467.388989, {
            'bytes': {'read': 897024, 'write': 0},
            'ios': {},
            'name': 'nvme0n1'
        }),
        'sda': (1637679467.388989, {
            'bytes': {},
            'ios': {},
            'name': 'sda'
        }),
    },
                 id="cgroup v2"),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_docker_container_diskstat_parse(info, expected_parsed):
    check = Check('docker_container_diskstat')
    parsed = check.run_parse(info)
    assert parsed == expected_parsed


@pytest.mark.usefixtures("config_load_all_checks")
def test_docker_container_diskstat_plugin_cgroupv2() -> None:
    plugin = agent_based_register.get_check_plugin(CheckPluginName("docker_container_diskstat"))
    parse_function = agent_based_register.get_section_plugin(
        SectionName("docker_container_diskstat")).parse_function
    assert plugin is not None

    # discovery function
    assert (list(plugin.discovery_function(
        parse_function(PLUGIN_OUTPUT_CGROUP_V2_0_SEC))) == [Service(item='SUMMARY')])  # type: ignore[arg-type]

    # check functions
    with pytest.raises(MKCounterWrapped):
        # no rate metrics yet
        _ = list(
            plugin.check_function(
                item="SUMMARY",
                params=FILESYSTEM_DEFAULT_LEVELS,
                section=parse_function(PLUGIN_OUTPUT_CGROUP_V2_0_SEC),  # type: ignore[arg-type]
            ))
    result = list(
        plugin.check_function(
            item="SUMMARY",
            params=FILESYSTEM_DEFAULT_LEVELS,
            section=parse_function(PLUGIN_OUTPUT_CGROUP_V2_272_SEC),  # type: ignore[arg-type]
        ))

    assert result == [
        Result(state=State.OK, summary='Read: 2.04 MB/s'),
        Metric('disk_read_throughput', 2137434.6930468315),
        Result(state=State.OK, summary='Write: 20.30 MB/s'),
        Metric('disk_write_throughput', 21282760.63304166),
    ]
