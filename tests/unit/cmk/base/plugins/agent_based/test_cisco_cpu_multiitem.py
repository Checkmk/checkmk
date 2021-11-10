#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State

from tests.unit.conftest import FixRegister


def test_check_cisco_cpu_multiitem(fix_register: FixRegister) -> None:
    parsed_section = fix_register.snmp_sections[SectionName("cisco_cpu_multiitem")].parse_function(
        [[["2001", "5"], ["3001", "10"]], [["2001", "cpu 2"], ["3001", "another cpu 3"]]]
    )
    plugin = fix_register.check_plugins[CheckPluginName("cisco_cpu_multiitem")]
    params = {"levels": [80, 90]}

    assert list(plugin.check_function(params=params, item="2", section=parsed_section)) == [
        Result(state=State.OK, summary="Utilization in the last 5 minutes: 5.0%"),
        Metric("util", 5.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]

    assert list(
        plugin.check_function(params=params, item="another cpu 3", section=parsed_section)
    ) == [
        Result(state=State.OK, summary="Utilization in the last 5 minutes: 10.0%"),
        Metric("util", 10.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]
