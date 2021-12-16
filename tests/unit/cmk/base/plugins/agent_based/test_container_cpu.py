#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base import item_state
from cmk.base.item_state import MKCounterWrapped
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State

# the following string tables should display 150% cpu usage
# two cpus were working at 75%

# agent running inside docker on a host with cgroupv1

DOCKER_CONTAINER_CPU_CGROUPV1_0 = [
    [
        "cpu",
        "764839",
        "1902",
        "277406",
        "5945752",
        "11165",
        "0",
        "18947",
        "0",
        "0",
        "0",
    ],
    ["num_cpus", "8"],
    ["user", "6196"],
    ["system", "141"],
]

DOCKER_CONTAINER_CPU_CGROUPV1_10 = [
    [
        "cpu",
        "766488",
        "1903",
        "277490",
        "5952056",
        "11168",
        "0",
        "18950",
        "0",
        "0",
        "0",
    ],
    ["num_cpus", "8"],
    ["user", "7707"],
    ["system", "146"],
]

# mk_docker.py running on a host with cgroupv1

MK_DOCKER_CONTAINER_CPU_CGROUPV1_0 = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}',
    ],
    [
        '{"cpu_usage": {"total_usage": 492596960696, "percpu_usage": [56412897570, 70863637554, 23303'
        '982576, 58690336091, 53612953212, 65956324201, 88398597623, 75358231869], "usage_in_kernelmo'
        'de": 1570000000, "usage_in_usermode": 490750000000}, "system_cpu_usage": 96928480000000, "on'
        'line_cpus": 8, "throttling_data": {"periods": 0, "throttled_periods": 0, "throttled_time": 0'
        "}}"
    ],
]

MK_DOCKER_CONTAINER_CPU_CGROUPV1_10 = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}',
    ],
    [
        '{"cpu_usage": {"total_usage": 510617797293, "percpu_usage": [56413193361, 78538845182, 27881'
        '010731, 58691607576, 53626502638, 67285721659, 92822615190, 75358300956], "usage_in_kernelmo'
        'de": 1580000000, "usage_in_usermode": 508750000000}, "system_cpu_usage": 97024520000000, "on'
        'line_cpus": 8, "throttling_data": {"periods": 0, "throttled_periods": 0, "throttled_time": 0'
        "}}"
    ],
]

# linux agent running inside a lxc container

LXC_CONTAINER_CPU_CGROUPV1_0 = [
    ["cpu", "1159255", "0", "0", "2397867272", "0", "0", "0", "0", "0", "0"],
    ["num_cpus", "2"],
    ["user", "706771"],
    ["system", "450382"],
]

LXC_CONTAINER_CPU_CGROUPV1_10 = [
    ["cpu", "1162904", "0", "0", "2397868462", "0", "0", "0", "0", "0", "0"],
    ["num_cpus", "2"],
    ["user", "710388"],
    ["system", "450408"],
]


@pytest.mark.parametrize(
    "section_name, plugin_name, string_table_0, string_table_10, num_cpu, util",
    [
        [
            "docker_container_cpu",
            "docker_container_cpu",
            DOCKER_CONTAINER_CPU_CGROUPV1_0,
            DOCKER_CONTAINER_CPU_CGROUPV1_10,
            8,
            150.77076081551465,
        ],
        [
            "docker_container_cpu",
            "docker_container_cpu",
            MK_DOCKER_CONTAINER_CPU_CGROUPV1_0,
            MK_DOCKER_CONTAINER_CPU_CGROUPV1_10,
            8,
            150.11109201999167,
        ],
        [
            "lxc_container_cpu",
            "lxc_container_cpu",
            LXC_CONTAINER_CPU_CGROUPV1_0,
            LXC_CONTAINER_CPU_CGROUPV1_10,
            2,
            150.56829923537921,
        ],
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_container_cpu_cgroupv1(
    section_name: str,
    plugin_name: str,
    string_table_0,
    string_table_10,
    num_cpu,
    util,
    mocker,
) -> None:

    # TODO: ist this the right way to do it? i doub it.
    # this will probably change global state which will be changed for other tests?!
    # make sure each test-run gets it's own counter values, otherwise MKCounterWrapped is not raised
    item_state.set_item_state_prefix(str(util))

    agent_section = agent_based_register.get_section_plugin(SectionName(section_name))
    plugin = agent_based_register.get_check_plugin(CheckPluginName(plugin_name))
    assert plugin
    section_0_seconds = agent_section.parse_function(string_table_0)
    section_10_seconds = agent_section.parse_function(string_table_10)
    with pytest.raises(MKCounterWrapped):
        # first run, no rate metrics yet:
        _ = list(plugin.check_function(params={}, section=section_0_seconds))
    # now we have a rate:
    assert list(plugin.check_function(params={}, section=section_10_seconds)) == [
        Result(state=State.OK, summary=f"Total CPU: {int(util)}%"),
        Metric("util", util, boundaries=(0.0, num_cpu * 100.0)),
    ]
