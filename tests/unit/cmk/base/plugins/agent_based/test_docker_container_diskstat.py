#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.render import iobandwidth
from cmk.base.plugins.agent_based.docker_container_diskstat_cgroupv2 import DockerDiskstatParser

# The following string tables are created by executing the following commands:
#   fio --name wxyz --direct=1 --buffered=0 --size=512m --bs=4k --rw=read --ioengine=sync --numjobs=1
#   fio --name wxyz --direct=1 --buffered=0 --size=1024m --bs=4k --rw=write --ioengine=sync --numjobs=1
# They will write 1024+512 MiB to disk, and read 512Mib. Over a timespan of 60 seconds this should result in:
#   read = 8947848 b/s
#   write = 26843546 b/s

# The following comments belong to the test data:

# check_mk_agent running inside a docker container

# docker stats reported:
# 0B / 232MB -> 1.07GB / 3.46GB
# read: 1.07GB / 60 s = 17833333 b/s (factor 2 off the theoretical value)
# write: 3228MB / 60 s = 53800000 b/s (factor 2 off the theoreitcal value)

DOCKER_CONTAINER_DISKSTAT_CGROUPV1_0 = [
    ["[time]"],
    ["1640097369"],
    ["[io_service_bytes]"],
    ["8:0", "Read", "0"],
    ["8:0", "Write", "115892224"],
    ["8:0", "Sync", "6500352"],
    ["8:0", "Async", "109391872"],
    ["8:0", "Total", "115892224"],
    ["Total", "115892224"],
    ["[io_serviced]"],
    ["8:0", "Read", "0"],
    ["8:0", "Write", "1805"],
    ["8:0", "Sync", "522"],
    ["8:0", "Async", "1283"],
    ["8:0", "Total", "1805"],
    ["Total", "1805"],
    ["[names]"],
    ["sda", "8:0"],
    ["sr0", "11:0"],
]

DOCKER_CONTAINER_DISKSTAT_CGROUPV1_60 = [
    ["[time]"],
    ["1640097429"],
    ["[io_service_bytes]"],
    ["8:0", "Read", "536870912"],
    ["8:0", "Write", "1727946752"],
    ["8:0", "Sync", "1618554880"],
    ["8:0", "Async", "646262784"],
    ["8:0", "Total", "2264817664"],
    ["Total", "2264817664"],
    ["[io_serviced]"],
    ["8:0", "Read", "131072"],
    ["8:0", "Write", "264465"],
    ["8:0", "Sync", "263182"],
    ["8:0", "Async", "132355"],
    ["8:0", "Total", "395537"],
    ["Total", "395537"],
    ["[names]"],
    ["sda", "8:0"],
    ["sr0", "11:0"],
]

MK_DOCKER_DOCKER_CONTAINER_DISKSTAT_CGROUPV1_0 = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "ApiVersion": "1.40", "DockerPyVersion": "2.6.1"}',
    ],
    [
        '{"io_queue_recursive": [{"value": 0, "op": "Read", "major": 8, "minor": 0}, {"value": 0, "op'
        '": "Write", "major": 8, "minor": 0}, {"value": 0, "op": "Sync", "major": 8, "minor": 0}, {"v'
        'alue": 0, "op": "Async", "major": 8, "minor": 0}, {"value": 0, "op": "Total", "major": 8, "m'
        'inor": 0}], "io_service_bytes_recursive": [{"value": 0, "op": "Read", "major": 8, "minor": 0'
        '}, {"value": 115892224, "op": "Write", "major": 8, "minor": 0}, {"value": 6500352, "op": "Sy'
        'nc", "major": 8, "minor": 0}, {"value": 109391872, "op": "Async", "major": 8, "minor": 0}, {'
        '"value": 115892224, "op": "Total", "major": 8, "minor": 0}, {"value": 0, "op": "Read", "majo'
        'r": 8, "minor": 0}, {"value": 115892224, "op": "Write", "major": 8, "minor": 0}, {"value": 6'
        '500352, "op": "Sync", "major": 8, "minor": 0}, {"value": 109391872, "op": "Async", "major": '
        '8, "minor": 0}, {"value": 115892224, "op": "Total", "major": 8, "minor": 0}], "io_service_ti'
        'me_recursive": [{"value": 0, "op": "Read", "major": 8, "minor": 0}, {"value": 581357937, "op'
        '": "Write", "major": 8, "minor": 0}, {"value": 204339427, "op": "Sync", "major": 8, "minor":'
        '0}, {"value": 377018510, "op": "Async", "major": 8, "minor": 0}, {"value": 581357937, "op": '
        '"Total", "major": 8, "minor": 0}], "time": 1640097371.652645, "io_wait_time_recursive": [{"v'
        'alue": 0, "op": "Read", "major": 8, "minor": 0}, {"value": 1149150164, "op": "Write", "major'
        '": 8, "minor": 0}, {"value": 1122235223, "op": "Sync", "major": 8, "minor": 0}, {"value": 26'
        '914941, "op": "Async", "major": 8, "minor": 0}, {"value": 1149150164, "op": "Total", "major"'
        ': 8, "minor": 0}], "sectors_recursive": [{"value": 226352, "op": "", "major": 8, "minor": 0}'
        '], "io_serviced_recursive": [{"value": 0, "op": "Read", "major": 8, "minor": 0}, {"value": 1'
        '805, "op": "Write", "major": 8, "minor": 0}, {"value": 522, "op": "Sync", "major": 8, "minor'
        '": 0}, {"value": 1283, "op": "Async", "major": 8, "minor": 0}, {"value": 1805, "op": "Total"'
        ', "major": 8, "minor": 0}, {"value": 0, "op": "Read", "major": 8, "minor": 0}, {"value": 180'
        '5, "op": "Write", "major": 8, "minor": 0}, {"value": 522, "op": "Sync", "major": 8, "minor":'
        '0}, {"value": 1283, "op": "Async", "major": 8, "minor": 0}, {"value": 1805, "op": "Total", "'
        'major": 8, "minor": 0}], "io_time_recursive": [{"value": 2017966265, "op": "", "major": 8, "'
        'minor": 0}], "names": {"8:0": "sda", "11:0": "sr0"}, "io_merged_recursive": [{"value": 0, "o'
        'p": "Read", "major": 8, "minor": 0}, {"value": 0, "op": "Write", "major": 8, "minor": 0}, {"'
        'value": 0, "op": "Sync", "major": 8, "minor": 0}, {"value": 0, "op": "Async", "major": 8, "m'
        'inor": 0}, {"value": 0, "op": "Total", "major": 8, "minor": 0}]}'
    ],
]

MK_DOCKER_DOCKER_CONTAINER_DISKSTAT_CGROUPV1_60 = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "ApiVersion": "1.40", "DockerPyVersion": "2.6.1"}',
    ],
    [
        '{"names": {"11:0": "sr0", "8:0": "sda"}, "io_merged_recursive": [{"value": 0, "minor": 0, "m'
        'ajor": 8, "op": "Read"}, {"value": 0, "minor": 0, "major": 8, "op": "Write"}, {"value": 0, "'
        'minor": 0, "major": 8, "op": "Sync"}, {"value": 0, "minor": 0, "major": 8, "op": "Async"}, {'
        '"value": 0, "minor": 0, "major": 8, "op": "Total"}], "io_wait_time_recursive": [{"value": 32'
        '7741887, "minor": 0, "major": 8, "op": "Read"}, {"value": 48900760071, "minor": 0, "major": '
        '8, "op": "Write"}, {"value": 48873845130, "minor": 0, "major": 8, "op": "Sync"}, {"value": 3'
        '54656828, "minor": 0, "major": 8, "op": "Async"}, {"value": 49228501958, "minor": 0, "major"'
        ': 8, "op": "Total"}], "sectors_recursive": [{"value": 4423472, "minor": 0, "major": 8, "op":'
        '""}], "time": 1640097433.218057, "io_serviced_recursive": [{"value": 131072, "minor": 0, "ma'
        'jor": 8, "op": "Read"}, {"value": 264465, "minor": 0, "major": 8, "op": "Write"}, {"value": '
        '263182, "minor": 0, "major": 8, "op": "Sync"}, {"value": 132355, "minor": 0, "major": 8, "op'
        '": "Async"}, {"value": 395537, "minor": 0, "major": 8, "op": "Total"}, {"value": 131072, "mi'
        'nor": 0, "major": 8, "op": "Read"}, {"value": 264465, "minor": 0, "major": 8, "op": "Write"}'
        ', {"value": 263182, "minor": 0, "major": 8, "op": "Sync"}, {"value": 132355, "minor": 0, "ma'
        'jor": 8, "op": "Async"}, {"value": 395537, "minor": 0, "major": 8, "op": "Total"}], "io_serv'
        'ice_bytes_recursive": [{"value": 536870912, "minor": 0, "major": 8, "op": "Read"}, {"value":'
        '1727946752, "minor": 0, "major": 8, "op": "Write"}, {"value": 1618554880, "minor": 0, "major'
        '": 8, "op": "Sync"}, {"value": 646262784, "minor": 0, "major": 8, "op": "Async"}, {"value": '
        '2264817664, "minor": 0, "major": 8, "op": "Total"}, {"value": 536870912, "minor": 0, "major"'
        ': 8, "op": "Read"}, {"value": 1727946752, "minor": 0, "major": 8, "op": "Write"}, {"value": '
        '1618554880, "minor": 0, "major": 8, "op": "Sync"}, {"value": 646262784, "minor": 0, "major":'
        '8, "op": "Async"}, {"value": 2264817664, "minor": 0, "major": 8, "op": "Total"}], "io_servic'
        'e_time_recursive": [{"value": 9490485126, "minor": 0, "major": 8, "op": "Read"}, {"value": 2'
        '8621999618, "minor": 0, "major": 8, "op": "Write"}, {"value": 28244981108, "minor": 0, "majo'
        'r": 8, "op": "Sync"}, {"value": 9867503636, "minor": 0, "major": 8, "op": "Async"}, {"value"'
        ': 38112484744, "minor": 0, "major": 8, "op": "Total"}], "io_queue_recursive": [{"value": 0, '
        '"minor": 0, "major": 8, "op": "Read"}, {"value": 0, "minor": 0, "major": 8, "op": "Write"}, '
        '{"value": 0, "minor": 0, "major": 8, "op": "Sync"}, {"value": 0, "minor": 0, "major": 8, "op'
        '": "Async"}, {"value": 0, "minor": 0, "major": 8, "op": "Total"}], "io_time_recursive": [{"v'
        'alue": 30284678714, "minor": 0, "major": 8, "op": ""}]}'
    ],
]

# those are gathered in a vm. could not get correct values on the developer machine.

DOCKER_CONTAINER_DISKSTAT_CGROUPV2_0 = [
    ["[time]"],
    ["1641207164"],
    ["[io.stat]"],
    [
        "8:0",
        "rbytes=0",
        "wbytes=139948032",
        "rios=0",
        "wios=2391",
        "dbytes=0",
        "dios=0",
    ],
    ["[names]"],
    ["sda", "8:0"],
    ["sr0", "11:0"],
]

DOCKER_CONTAINER_DISKSTAT_CGROUPV2_60 = [
    ["[time]"],
    ["1641207225"],
    ["[io.stat]"],
    [
        "8:0",
        "rbytes=536879104",
        "wbytes=1750560768",
        "rios=131074",
        "wios=264986",
        "dbytes=0",
        "dios=0",
    ],
    ["[names]"],
    ["sda", "8:0"],
    ["sr0", "11:0"],
]

# rios and wios are missing. config: debian testing with kernel 5.10.84 and docker 20.10.5+dfsg1

MK_DOCKER_DOCKER_CONTAINER_DISKSTAT_CGROUPV2_0 = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}',
    ],
    [
        '{"io_service_bytes_recursive": [{"major": 8, "minor": 0, "op": "read", "value": 0}, {"major"'
        ': 8, "minor": 0, "op": "write", "value": 139948032}], "io_serviced_recursive": null, "io_que'
        'ue_recursive": null, "io_service_time_recursive": null, "io_wait_time_recursive": null, "io_'
        'merged_recursive": null, "io_time_recursive": null, "sectors_recursive": null, "time": 16412'
        '07165.4858, "names": {"11:0": "sr0", "8:0": "sda"}}'
    ],
]
MK_DOCKER_DOCKER_CONTAINER_DISKSTAT_CGROUPV2_60 = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}',
    ],
    [
        '{"io_service_bytes_recursive": [{"major": 8, "minor": 0, "op": "read", "value": 536879104}, '
        '{"major": 8, "minor": 0, "op": "write", "value": 1750560768}], "io_serviced_recursive": null'
        ', "io_queue_recursive": null, "io_service_time_recursive": null, "io_wait_time_recursive": n'
        'ull, "io_merged_recursive": null, "io_time_recursive": null, "sectors_recursive": null, "tim'
        'e": 1641207226.9843512, "names": {"11:0": "sr0", "8:0": "sda"}}'
    ],
]


def test_parser() -> None:
    # we had a little discussion about instance variables vs. class variable
    # this test make sure to only use instance variables for the data stored.
    # otherwise the second run would include data from the first run.
    parser = DockerDiskstatParser()
    parser.parse([["[names]"], ["1", "a"]])
    assert parser.names.names == {"a": "1"}
    parser = DockerDiskstatParser()
    parser.parse([["[names]"], ["2", "b"]])
    assert parser.names.names == {"b": "2"}


@pytest.mark.parametrize(
    "section_name, plugin_name, string_table_0, string_table_10, read_bytes, write_bytes, read_ops, write_ops",
    [
        [
            "docker_container_diskstat",
            "diskstat",
            DOCKER_CONTAINER_DISKSTAT_CGROUPV1_0,
            DOCKER_CONTAINER_DISKSTAT_CGROUPV1_60,
            8947848.533333333,
            26867575.466666665,
            2184.5333333333333,
            4377.666666666667,
        ],
        [
            "docker_container_diskstat",
            "diskstat",
            MK_DOCKER_DOCKER_CONTAINER_DISKSTAT_CGROUPV1_0,
            MK_DOCKER_DOCKER_CONTAINER_DISKSTAT_CGROUPV1_60,
            8720333.321099441,
            26184418.82719776,
            2128.9876272215433,
            4266.356583908161,
        ],
        [
            "docker_container_diskstat_cgroupv2",
            "diskstat",
            DOCKER_CONTAINER_DISKSTAT_CGROUPV2_0,
            DOCKER_CONTAINER_DISKSTAT_CGROUPV2_60,
            8801296.786885247,
            26403487.475409836,
            2148.754098360656,
            4304.836065573771,
        ],
        [
            "docker_container_diskstat",
            "diskstat",
            MK_DOCKER_DOCKER_CONTAINER_DISKSTAT_CGROUPV2_0,
            MK_DOCKER_DOCKER_CONTAINER_DISKSTAT_CGROUPV2_60,
            8729947.19603285,
            26189441.968927883,
            0,
            0,
        ],
    ],
)
def test_docker_container_diskstat(
    fix_register,
    section_name: str,
    plugin_name: str,
    string_table_0,
    string_table_10,
    read_bytes,
    write_bytes,
    read_ops,
    write_ops,
) -> None:
    agent_section = fix_register.agent_sections[SectionName(section_name)]
    plugin = fix_register.check_plugins[CheckPluginName(plugin_name)]

    section_0_seconds = agent_section.parse_function(string_table_0)
    section_60_seconds = agent_section.parse_function(string_table_10)
    with pytest.raises(IgnoreResultsError):
        # first run, no rate metrics yet:
        _ = list(
            plugin.check_function(
                params={},
                section_multipath=None,
                section_diskstat=section_0_seconds,
                item="SUMMARY",
            )
        )
    # now we have a rate:
    result = list(
        plugin.check_function(
            params={},
            section_multipath=None,
            section_diskstat=section_60_seconds,
            item="SUMMARY",
        )
    )

    expected_result = [
        Result(state=State.OK, summary=f"Read: {iobandwidth(read_bytes)}"),
        Metric("disk_read_throughput", read_bytes),
        Result(state=State.OK, summary=f"Write: {iobandwidth(write_bytes)}"),
        Metric("disk_write_throughput", write_bytes),
    ]
    if write_ops != 0 and read_ops != 0:
        expected_result += [
            Result(state=State.OK, notice=f"Read operations: {read_ops:.2f}/s"),
            Metric("disk_read_ios", read_ops),
            Result(state=State.OK, notice=f"Write operations: {write_ops:.2f}/s"),
            Metric("disk_write_ios", write_ops),
        ]
    assert result == expected_result


@pytest.mark.parametrize(
    "section_name, plugin_name, string_table_0",
    [
        [
            "docker_container_diskstat",
            "diskstat",
            DOCKER_CONTAINER_DISKSTAT_CGROUPV1_0,
        ],
        [
            "docker_container_diskstat",
            "diskstat",
            MK_DOCKER_DOCKER_CONTAINER_DISKSTAT_CGROUPV1_0,
        ],
    ],
)
@pytest.mark.parametrize(
    "discovery_mode, expected_item",
    [
        ["summary", "SUMMARY"],
        ["physical", "sda"],
    ],
)
def test_docker_container_diskstat_discovery(
    section_name: str,
    plugin_name: str,
    mocker,
    discovery_mode,
    string_table_0,
    fix_register,
    expected_item,
) -> None:
    agent_section = fix_register.agent_sections[SectionName(section_name)]
    plugin = fix_register.check_plugins[CheckPluginName(plugin_name)]

    assert plugin
    section_0_seconds = agent_section.parse_function(string_table_0)
    assert list(
        plugin.discovery_function(
            [discovery_mode], section_diskstat=section_0_seconds, section_multipath=None
        )
    ) == [Service(item=expected_item)]
