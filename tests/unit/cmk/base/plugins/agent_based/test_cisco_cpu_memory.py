#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

Section = Mapping  # for now


# remove after migration
@pytest.fixture(name="parse_cisco_cpu_memory_multiitem", scope="module")
def _get_parse_cisco_cpu_memory(fix_register: FixRegister):
    section_plugin = fix_register.snmp_sections[SectionName("cisco_cpu_memory")]
    return section_plugin.parse_function


# remove after migration
@pytest.fixture(name="discover_cisco_cpu_memory_multiitem", scope="module")
def _get_discover_cisco_cpu_memory(fix_register: FixRegister):
    plugin = fix_register.check_plugins[CheckPluginName("cisco_cpu_memory")]
    return lambda s: plugin.discovery_function(section=s)


# remove after migration
@pytest.fixture(name="check_cisco_cpu_memory_multiitem", scope="module")
def _get_check_cisco_cpu_memory(fix_register: FixRegister):
    plugin = fix_register.check_plugins[CheckPluginName("cisco_cpu_memory")]
    return lambda i, p, s: plugin.check_function(item=i, params=p, section=s)


def test_parsing(parse_cisco_cpu_memory_multiitem) -> None:
    assert parse_cisco_cpu_memory_multiitem(
        [
            [["1", "1", "1", "1"], ["2", "0", "0", "0"]],
            [["1", "CPU of Module 1"], ["2", "CPU of Module 2"]],
        ]
    ) == {"of Module 1": {"mem_free": 1024.0, "mem_reserved": 1024.0, "mem_used": 1024.0}}


STRING_TABLE = [
    [["11000", "3343553", "565879", "284872"]],
    [
        ["1", "Virtual Stack"],
        ["25", "Switch1 Container of Power Supply Bay"],
        ["11000", "Switch2 Supervisor 1 (virtual slot 11)"],
    ],
]


@pytest.fixture(name="section", scope="module")
def _get_section(parse_cisco_cpu_memory_multiitem) -> Section:
    return parse_cisco_cpu_memory_multiitem(STRING_TABLE)


def test_discovery(discover_cisco_cpu_memory_multiitem, section: Section) -> None:
    assert list(discover_cisco_cpu_memory_multiitem(section)) == [
        Service(item="Switch2 Supervisor 1 (virtual slot 11)"),
    ]


def test_check_no_levels(check_cisco_cpu_memory_multiitem, section: Section) -> None:
    assert list(
        check_cisco_cpu_memory_multiitem("Switch2 Supervisor 1 (virtual slot 11)", {}, section)
    ) == [
        Result(state=State.OK, summary="Usage: 92.81% - 3.46 GiB of 3.73 GiB"),
        Metric("mem_used_percent", 92.81207602536634, boundaries=(0.0, None)),
    ]


def test_check_used_levels(check_cisco_cpu_memory_multiitem, section: Section) -> None:
    assert list(
        check_cisco_cpu_memory_multiitem(
            "Switch2 Supervisor 1 (virtual slot 11)", {"levels": (50.0, 90.0)}, section
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Usage: 92.81% - 3.46 GiB of 3.73 GiB (warn/crit at 50.00%/90.00% used)",
        ),
        Metric("mem_used_percent", 92.81207602536634, levels=(50.0, 90.0), boundaries=(0.0, None)),
    ]


def test_check_free_levels(check_cisco_cpu_memory_multiitem, section: Section) -> None:
    assert list(
        check_cisco_cpu_memory_multiitem(
            "Switch2 Supervisor 1 (virtual slot 11)", {"levels": (-20.0, -10.0)}, section
        )
    ) == [
        Result(
            state=State.CRIT,
            summary="Usage: 92.81% - 3.46 GiB of 3.73 GiB (warn/crit below 20.00%/10.00% free)",
        ),
        Metric(
            "mem_used_percent",
            92.81207602536634,
            levels=(80.0, 89.99999999999999),
            boundaries=(0.0, None),
        ),
    ]
