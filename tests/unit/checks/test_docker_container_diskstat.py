#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
import os
from typing import Tuple

import pytest

from tests.testlib import Check

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.check_api import MKCounterWrapped
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.utils.df import FILESYSTEM_DEFAULT_LEVELS

from .checktestlib import assertDiscoveryResultsEqual, DiscoveryResult, mock_item_state

pytestmark = pytest.mark.checks


INFO_MISSING_COUNTERS = [
    ['@docker_version_info', '{"PluginVersion": "0.1", "DockerPyVersion": "3.7.0", "ApiVersion": "1.38"}'],
    ['{"io_service_time_recursive": [], "sectors_recursive": [], "io_service_bytes_recursive": [], "io_serviced_recursive": [], "io_time_recursive": [], "names"    : {"7:9": "loop9", "8:0": "sda", "7:8": "loop8", "8:16": "sdb", "253:1": "dm-1", "253:0": "dm-0", "7:4": "loop4", "253:2": "dm-2", "7:2": "loop2", "7:3":     "loop3", "7:0": "loop0", "7:1": "loop1", "7:10": "loop10", "7:6": "loop6", "7:12": "loop12", "7:13": "loop13", "7:7": "loop7", "8:32": "sdc", "7:5": "loop    5", "7:11": "loop11"}, "time": 1568705427.380945, "io_queue_recursive": [], "io_merged_recursive": [], "io_wait_time_recursive": []}'],
]

INFO = [
    ['@docker_version_info', '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}'],
    [
        # original spaces where removed to save some space.
        '{"io_service_bytes_recursive":[{"major":253,"minor":2,"op":"Read","value":8192},{"major":253,"minor"'
        ':2,"op":"Write","value":0},{"major":253,"minor":2,"op":"Sync","value":8192},{"major":253,"minor":2,"'
        'op":"Async","value":0},{"major":253,"minor":2,"op":"Discard","value":0},{"major":253,"minor":2,"op":'
        '"Total","value":8192},{"major":253,"minor":0,"op":"Write","value":0},{"major":253,"minor":0,"op":"Sy'
        'nc","value":212992},{"major":253,"minor":0,"op":"Async","value":0},{"major":253,"minor":0,"op":"Disc'
        'ard","value":0},{"major":253,"minor":0,"op":"Total","value":212992},{"major":253,"minor":1,"op":"Rea'
        'd","value":204800},{"major":253,"minor":1,"op":"Write","value":0},{"major":253,"minor":1,"op":"Sync"'
        ',"value":204800},{"major":253,"minor":1,"op":"Async","value":0},{"major":253,"minor":1,"op":"Discard'
        '","value":0},{"major":253,"minor":1,"op":"Total","value":204800}],"io_serviced_recursive":[{"major":'
        '253,"minor":2,"op":"Read","value":2},{"major":253,"minor":2,"op":"Write","value":0},{"major":253,"mi'
        'nor":2,"op":"Sync","value":2},{"major":253,"minor":2,"op":"Async","value":0},{"major":253,"minor":2,'
        '"op":"Discard","value":0},{"major":253,"minor":2,"op":"Total","value":2},{"major":253,"minor":0,"op"'
        ':"Write","value":0},{"major":253,"minor":0,"op":"Sync","value":4},{"major":253,"minor":0,"op":"Async'
        '","value":0},{"major":253,"minor":0,"op":"Discard","value":0},{"major":253,"minor":0,"op":"Total","v'
        'alue":4},{"major":253,"minor":1,"op":"Read","value":2},{"major":253,"minor":1,"op":"Write","value":0'
        '},{"major":253,"minor":1,"op":"Sync","value":2},{"major":253,"minor":1,"op":"Async","value":0},{"maj'
        'or":253,"minor":1,"op":"Discard","value":0},{"major":253,"minor":1,"op":"Total","value":2}],"io_queu'
        'e_recursive":[],"io_service_time_recursive":[],"io_wait_time_recursive":[],"io_merged_recursive":[],'
        '"io_time_recursive":[],"sectors_recursive":[],"time":1613132235.7151694,"names":{"253:1":"dm-1","253'
        ':2":"dm-2","253:0":"dm-0"}}'
    ]
]

INFO_AGENT_INSIDE_CONTAINER = [
    ["[time]"],
    ["1613653450"],
    ["[io_service_bytes]"],
    ["8:0", "Read", "0"],
    ["8:0", "Write", "17403904"],
    ["8:0", "Sync", "1536000"],
    ["8:0", "Async", "15867904"],
    ["8:0", "Discard", "0"],
    ["8:0", "Total", "17403904"],
    ["Total", "17403904"],
    ["[io_serviced]"],
    ["8:0", "Read", "0"],
    ["8:0", "Write", "107"],
    ["8:0", "Sync", "83"],
    ["8:0", "Async", "24"],
    ["8:0", "Discard", "0"],
    ["8:0", "Total", "107"],
    ["Total", "107"],
    ["[names]"],
    ["sda", "8:0"],
    ["sr0", "11:0"],
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


def test_docker_container_diskstat_wrapped():
    check = Check('docker_container_diskstat')
    parsed = check.run_parse(INFO_MISSING_COUNTERS)

    with pytest.raises(MKCounterWrapped):
        check.run_check("SUMMARY", {}, parsed)

    with mock_item_state((0, 0)):
        # raise MKCounterWrapped anyway, because counters are missing in info
        with pytest.raises(MKCounterWrapped):
            check.run_check("SUMMARY", {}, parsed)


@pytest.mark.parametrize("info, discovery_expected", [
    (INFO_MISSING_COUNTERS, DiscoveryResult([("SUMMARY", {})])),
])
def test_docker_container_diskstat_discovery(info, discovery_expected):
    check = Check('docker_container_diskstat')
    parsed = check.run_parse(info)
    discovery_actual = DiscoveryResult(check.run_discovery(parsed))
    assertDiscoveryResultsEqual(check, discovery_actual, discovery_expected)


def test_docker_container_diskstat_check(mocker, monkeypatch):
    mocker.patch("cmk.base.item_state._get_counter", return_value=[None, 2.22])
    check = Check('docker_container_diskstat')
    result = check.run_check('dm-1', {}, check.run_parse(INFO))
    assert list(result) == [
        (0, 'Read: 2.22 B/s', [('disk_read_throughput', 2.22, None, None)]),
        (0, 'Write: 2.22 B/s', [('disk_write_throughput', 2.22, None, None)]),
        (0, 'Read operations: 2.22 1/s', [('disk_read_ios', 2.22, None, None)]),
        (0, 'Write operations: 2.22 1/s', [('disk_write_ios', 2.22, None, None)]),
    ]


def _load_parse_function():
    context = {'Tuple': Tuple, 'check_info': {}, }
    with open(os.path.join(os.path.dirname(__file__), '../../../checks/docker_container_diskstat')) as fo:
        exec(fo.read(), context)
    parse_docker_container_diskstat = context['parse_docker_container_diskstat']
    assert callable(parse_docker_container_diskstat)
    return parse_docker_container_diskstat


def test_parse_docker_container_diskstat_agent_inside_docker_container():
    parse_docker_container_diskstat = _load_parse_function()
    assert parse_docker_container_diskstat(INFO_AGENT_INSIDE_CONTAINER) == {
        'sda': (
            1613653450, {
                'name': 'sda',
                'bytes': {
                    'Async': 15867904,
                    'Discard': 0,
                    'Read': 0,
                    'Sync': 1536000,
                    'Total': 17403904,
                    'Write': 17403904},
                'ios': {
                    'Async': 24,
                    'Discard': 0,
                    'Read': 0,
                    'Sync': 83,
                    'Total': 107,
                    'Write': 107},
            }
        ),
    }


def test_parse_docker_container_diskstat():
    parse_docker_container_diskstat = _load_parse_function()
    assert parse_docker_container_diskstat(INFO) == {
        'dm-0': (1613132235.7151694, {
            'bytes': {
                'Async': 0,
                'Discard': 0,
                'Sync': 212992,
                'Total': 212992,
                'Write': 0
            },
            'ios': {
                'Async': 0,
                'Discard': 0,
                'Sync': 4,
                'Total': 4,
                'Write': 0
            },
            'name': 'dm-0'
        }),
        'dm-1': (1613132235.7151694, {
            'bytes': {
                'Async': 0,
                'Discard': 0,
                'Read': 204800,
                'Sync': 204800,
                'Total': 204800,
                'Write': 0
            },
            'ios': {
                'Async': 0,
                'Discard': 0,
                'Read': 2,
                'Sync': 2,
                'Total': 2,
                'Write': 0
            },
            'name': 'dm-1'
        }),
        'dm-2': (1613132235.7151694, {
            'bytes': {
                'Async': 0,
                'Discard': 0,
                'Read': 8192,
                'Sync': 8192,
                'Total': 8192,
                'Write': 0
            },
            'ios': {
                'Async': 0,
                'Discard': 0,
                'Read': 2,
                'Sync': 2,
                'Total': 2,
                'Write': 0
            },
            'name': 'dm-2'
        }),
    }


def test_docker_container_diskstat_plugin_cgroupv2(fix_register: FixRegister) -> None:
    parse_function = fix_register.agent_sections[SectionName("docker_container_diskstat")].parse_function
    plugin = fix_register.check_plugins[CheckPluginName("docker_container_diskstat")]

    # discovery function
    assert (
        list(
            plugin.discovery_function(
                parse_function(PLUGIN_OUTPUT_CGROUP_V2_0_SEC)
            )
        )
        == [Service(item='SUMMARY')]
    )

    # check functions
    with pytest.raises(MKCounterWrapped):
        # no rate metrics yet
        _ = list(
            plugin.check_function(
                item="SUMMARY",
                params=FILESYSTEM_DEFAULT_LEVELS,
                section=parse_function(PLUGIN_OUTPUT_CGROUP_V2_0_SEC),
            )
        )
    result = list(
        plugin.check_function(
            item="SUMMARY",
            params=FILESYSTEM_DEFAULT_LEVELS,
            section=parse_function(PLUGIN_OUTPUT_CGROUP_V2_272_SEC),
        )
    )

    assert result == [
        Result(state=State.OK, summary='Read: 2.04 MB/s'),
        Metric('disk_read_throughput', 2137434.6930468315),
        Result(state=State.OK, summary='Write: 20.30 MB/s'),
        Metric('disk_write_throughput', 21282760.63304166),
    ]
