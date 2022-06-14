#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.infoblox_services import (
    check_infoblox_services,
    discovery_infoblox_services,
    parse_infoblox_services,
)

example_snmp_string_table = [
    [
        ["9", "1", "Running"],
        ["10", "1", "2% - Primary drive usage is OK."],
        ["11", "1", "11.112.133.14"],
        ["12", "5", ""],
        ["13", "5", ""],
        ["14", "1", "11.112.133.204"],
        ["15", "5", ""],
        ["16", "1", "14% - System memory usage is OK."],
        ["17", "1", "Online"],
        ["18", "1", "16% - Database capacity usage is OK."],
        ["19", "5", ""],
        ["20", "5", ""],
        ["21", "5", ""],
        ["22", "5", ""],
        ["23", "5", ""],
        ["24", "5", ""],
        ["25", "5", ""],
        ["26", "5", ""],
        ["27", "5", ""],
        ["28", "1", "FAN 1: 8725 RPM"],
        ["29", "1", "FAN 2: 8725 RPM"],
        ["30", "1", "FAN 3: 8725 RPM"],
        ["31", "5", "Fan does not exist"],
        ["32", "5", "Fan does not exist"],
        ["33", "5", "Fan does not exist"],
        ["34", "5", "Fan does not exist"],
        ["35", "5", "Fan does not exist"],
        ["36", "1", "Power1 OK"],
        ["37", "5", "No power information available."],
        ["38", "1", "The NTP service resumed synchronization."],
        ["39", "1", "CPU_TEMP: +36.00 C"],
        ["40", "5", "No temperature information available."],
        ["41", "1", "SYS_TEMP: +34.00 C"],
        ["42", "5", ""],
        ["43", "1", "CPU Usage: 5%"],
        ["44", "4", ""],
        ["45", "4", ""],
        ["46", "5", ""],
        ["47", "5", ""],
        ["48", "5", ""],
        ["49", "5", "Reporting Service is inactive"],
        ["50", "5", ""],
        ["51", "4", ""],
        ["52", "1", "0% - System swap space usage is OK."],
        ["53", "5", "Discovery Consolidator Service is inactive"],
        ["54", "5", "Discovery Collector Service is inactive"],
        ["55", "1", "0% - Discovery capacity usage is OK."],
        ["56", "5", "Threat Protection Service is inactive"],
        ["57", "5", "Cloud API service is inactive."],
    ]
]

example_parsed_data = {
    "node-status": ("working", "Running"),
    "disk-usage": ("working", "2% - Primary drive usage is OK."),
    "enet-lan": ("working", "11.112.133.14"),
    "enet-mgmt": ("working", "11.112.133.204"),
    "memory": ("working", "14% - System memory usage is OK."),
    "replication": ("working", "Online"),
    "db-object": ("working", "16% - Database capacity usage is OK."),
    "fan1": ("working", "FAN 1: 8725 RPM"),
    "fan2": ("working", "FAN 2: 8725 RPM"),
    "fan3": ("working", "FAN 3: 8725 RPM"),
    "power-supply1": ("working", "Power1 OK"),
    "ntp-sync": ("working", "The NTP service resumed synchronization."),
    "cpu1-temp": ("working", "CPU_TEMP: +36.00 C"),
    "sys-temp": ("working", "SYS_TEMP: +34.00 C"),
    "cpu-usage": ("working", "CPU Usage: 5%"),
    "swap-usage": ("working", "0% - System swap space usage is OK."),
    "discovery-capacity": ("working", "0% - Discovery capacity usage is OK."),
}


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        (example_snmp_string_table, example_parsed_data),
    ],
)
def test_parse_infoblox_services(string_table, expected_parsed_data) -> None:
    assert parse_infoblox_services(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "section,result",
    [
        (example_parsed_data, [Service(item=key) for key in example_parsed_data]),
    ],
)
def test_discovery_infoblox_services(section, result) -> None:
    assert list(discovery_infoblox_services(section)) == result


@pytest.mark.parametrize(
    "item,section,result",
    [
        (
            "memory",
            example_parsed_data,
            [Result(state=state.OK, summary="Status: working (14% - System memory usage is OK.)")],
        ),
    ],
)
def test_check_infoblox_services(item, section, result) -> None:
    assert list(check_infoblox_services(item, section)) == result
