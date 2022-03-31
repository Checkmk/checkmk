#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.cisco_cpu_multiitem import (
    check_cisco_cpu_multiitem,
    CPUInfo,
    discover_cisco_cpu_multiitem,
    DISCOVERY_DEFAULT_PARAMETERS,
    Params,
    parse_cisco_cpu_multiitem,
    Section,
)


@pytest.fixture(name="parsed_section")
def parsed_section_fixture() -> Section:
    return parse_cisco_cpu_multiitem(
        [
            [
                ["1", "2001", "5"],
                ["2", "3001", "10"],
                ["3", "4001", "10"],
            ],
            [
                ["2001", "cpu 2", "12"],
                ["3001", "another cpu 3", "12"],
                ["4001", "A FAN", "7"],
            ],
        ]
    )


def test_check_cisco_cpu_multiitem(parsed_section: Section) -> None:
    params = Params({"levels": (80, 90)})

    assert list(check_cisco_cpu_multiitem("2", params, parsed_section)) == [
        Result(state=State.OK, summary="Utilization in the last 5 minutes: 5.00%"),
        Metric("util", 5.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]

    assert list(check_cisco_cpu_multiitem("another cpu 3", params, parsed_section)) == [
        Result(state=State.OK, summary="Utilization in the last 5 minutes: 10.00%"),
        Metric("util", 10.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]

    assert list(check_cisco_cpu_multiitem("average", params, parsed_section)) == [
        Result(state=State.OK, summary="Utilization in the last 5 minutes: 7.50%"),
        Metric("util", 7.5, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]

    assert list(check_cisco_cpu_multiitem("not_found", params, parsed_section)) == []


@pytest.mark.parametrize(
    "discovery_params, expected_discovery_result",
    (
        pytest.param(
            DISCOVERY_DEFAULT_PARAMETERS,
            [
                Service(item="2"),
                Service(item="another cpu 3"),
            ],
            id="default discovery params: individual only",
        ),
        pytest.param(
            {"individual": False, "average": True},
            [
                Service(item="average"),
            ],
            id="discover average only",
        ),
        pytest.param(
            {"individual": True, "average": True},
            [
                Service(item="2"),
                Service(item="another cpu 3"),
                Service(item="average"),
            ],
            id="discover both: average and individual",
        ),
        pytest.param(
            {"individual": False, "average": False},
            [],
            id="discover none",
        ),
    ),
)
def test_discover_cisco_cpu_multiitem(
    parsed_section: Section, discovery_params, expected_discovery_result
) -> None:
    assert (
        list(discover_cisco_cpu_multiitem(discovery_params, parsed_section))
        == expected_discovery_result
    )


def test_ignore_non_cpu_entities() -> None:
    # chassis can actually have cpus!
    assert parse_cisco_cpu_multiitem(
        [
            [
                ["1", "2001", "5"],
                ["2", "3001", "10"],
            ],
            [
                ["2001", "FAN", "7"],
                ["3001", "Chassis", "3"],
            ],
        ]
    ) == {
        "Chassis": CPUInfo(util=10.0),
        "average": CPUInfo(util=10.0),
    }


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
            "average": CPUInfo(util=1.0),
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
            "average": CPUInfo(util=7.0),
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
            "average": CPUInfo(util=25.0),
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
            "average": CPUInfo(util=10.0),
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
            "average": CPUInfo(util=36.0),
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
            "average": CPUInfo(util=3.5),
        },
        id="cisco_c9200l_stack",
    ),
]


@pytest.mark.parametrize("string_table, expected", data)
def test_parse(string_table, expected) -> None:
    assert parse_cisco_cpu_multiitem(string_table) == expected
