#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.liebert.agent_based.lib import Section
from cmk.plugins.liebert.agent_based.liebert_cooling_position import (
    check_plugin_liebert_cooling_position,
    snmp_section_liebert_cooling_position,
)


def _section() -> Section:
    assert (
        section := snmp_section_liebert_cooling_position.parse_function(
            [
                [
                    ["Free Cooling Valve Open Position", "42", "%"],
                    ["This is ignored", "42", "%"],
                ]
            ]
        )
    ) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_liebert_cooling_position.discovery_function(_section())) == [
        Service(item="Free Cooling Valve Open Position"),
    ]


def test_check() -> None:
    assert list(
        check_plugin_liebert_cooling_position.check_function(
            "Free Cooling Valve Open Position", {"min_capacity": (50, 45)}, _section()
        )
    ) == [
        Result(state=State.CRIT, summary="42.00 % (warn/crit below 50.00 %/45.00 %)"),
        Metric("capacity_perc", 42.0),
    ]
