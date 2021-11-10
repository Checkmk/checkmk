#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.cisco_cpu_multiitem import (
    discover_cisco_cpu_multiitem,
    parse_cisco_cpu_multiitem,
    Section,
)

from tests.unit.conftest import FixRegister


@pytest.fixture(name="parsed_section")
def parsed_section_fixture() -> Section:
    return parse_cisco_cpu_multiitem(
        [[["2001", "5"], ["3001", "10"]], [["2001", "cpu 2"], ["3001", "another cpu 3"]]]
    )


def test_check_cisco_cpu_multiitem(fix_register: FixRegister, parsed_section: Section) -> None:
    plugin = fix_register.check_plugins[CheckPluginName("cisco_cpu_multiitem")]
    params = {"levels": (80, 90)}

    assert list(plugin.check_function(params=params, item="2", section=parsed_section)) == [
        Result(state=State.OK, summary="Utilization in the last 5 minutes: 5.00%"),
        Metric("util", 5.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]

    assert list(
        plugin.check_function(params=params, item="another cpu 3", section=parsed_section)
    ) == [
        Result(state=State.OK, summary="Utilization in the last 5 minutes: 10.00%"),
        Metric("util", 10.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]


def test_discover_cisco_cpu_multiitem(parsed_section: Section) -> None:
    assert list(discover_cisco_cpu_multiitem(parsed_section)) == [
        Service(item="2"),
        Service(item="another cpu 3"),
    ]
