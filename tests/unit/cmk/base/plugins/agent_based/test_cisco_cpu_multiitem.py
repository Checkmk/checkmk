#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import SectionName

import cmk.base.api.agent_based.register as agent_based_register


def CPUInfo(util):
    # hack to make it compatible with master branch
    return {"util": util}


data = [
    pytest.param(
        [
            # Number of CPUs: 1
            # Remark: only one entry in 109er table
            [
                ["1", "0", "1"],
            ],
            [
                ["1", "CISCO2921/K9", "3"],
                ["2", "C2921 Chassis Slot 0", "5"],
                ["3", "C2921 Mother board 3GE, integrated VPN and 4W on Slot 0", "9"],
                ["4", "DaughterCard Slot 0 on Card 0", "5"],
            ],
        ],
        {
            "1": CPUInfo(util=1.0),
        },
        id="cisco_router_c2921",
    ),
    pytest.param(
        [
            # Number of CPUs: 1
            # Remark: here, the physical name is replaced with `???`
            [
                ["1", "0", "7"],
            ],
            [
                ["1001", "???", "3"],
            ],
        ],
        {
            "1": CPUInfo(util=7.0),
        },
        id="cisco_switch_c2960",
    ),
    pytest.param(
        [
            # Number of CPUs: 4 (but in enity table we see 8 CPUs + 1 chassis)
            # CPU 2+3 are directly referenced, 1 and 4 only virtual
            [
                ["1", "0", "10"],
                ["2", "2", "20"],
                ["3", "3", "30"],
                ["4", "0", "40"],
            ],
            [
                # the names are no original data, but derived from the descirption
                ["1", "1 firepower", "3"],
                ["2", "2 cpu", "12"],
                ["3", "3 cpu", "12"],
                ["4", "4 cpu", "12"],
                ["5", "5 cpu", "12"],
                ["6", "6 cpu", "12"],
                ["7", "7 cpu", "12"],
                ["8", "8 accelerator", "12"],
                ["9", "9 slot", "12"],
            ],
        ],
        {
            "1": CPUInfo(util=10.0),
            "2 cpu": CPUInfo(util=20.0),
            "3 cpu": CPUInfo(util=30.0),
            "4": CPUInfo(util=40.0),
        },
        id="cisco_asa_5508_x",
    ),
    pytest.param(
        [
            # Number of CPUs: one or two... we're not sure...
            # Remark: Item 9001 is not listed in CPU table... so we also do not have a value for it...
            [
                ["7", "7035", "10"],
            ],
            [
                ["7035", "CPU 7035 ???", "12"],
                ["9001", "CPU 9001 ???", "12"],
            ],
        ],
        {
            "7035 ???": CPUInfo(util=10.0),
        },
        id="cisco_isr_router",
    ),
    pytest.param(
        [
            [
                ["1", "1001", "36"],
            ],
            [
                ["1", "1 ???", "11"],
                ["1001", "CPU 1001 ???", "3"],
                ["1002", "1002 ???", "9"],
            ],
        ],
        {
            "1001 ???": CPUInfo(util=36.0),
        },
        id="cisco_c2960x_stack",
    ),
    pytest.param(
        [
            # Number of CPUs: 2
            # Remark: Total5minRev is dummy data.
            [
                ["11", "1000", "3"],
                ["12", "2000", "4"],
            ],
            [
                ["1", "???", "11"],
                ["1000", "CPU 1000", "3"],
                ["1001", "???", "1"],
                ["2000", "CPU 2000", "3"],
            ],
        ],
        {
            "1000": CPUInfo(util=3.0),
            "2000": CPUInfo(util=4.0),
        },
        id="cisco_c9200l_stack",
    ),
]


@pytest.mark.parametrize("string_table, expected", data)
@pytest.mark.usefixtures("config_load_all_checks")
def test_parse(string_table, expected) -> None:
    plugin = agent_based_register.get_section_plugin(SectionName("cisco_cpu_multiitem"))
    assert plugin
    assert plugin.parse_function(string_table) == expected
