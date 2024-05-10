#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.liebert.agent_based.lib import Section
from cmk.plugins.liebert.agent_based.liebert_cooling import (
    check_plugin_liebert_cooling,
    snmp_section_liebert_cooling,
)


def _section() -> Section[float]:
    assert (
        section := snmp_section_liebert_cooling.parse_function(
            [
                [
                    ["Cooling Capacity (Primary)", "42", "%"],
                    ["Cooling Capacity (Secondary)", "42", "%"],
                ]
            ]
        )
    ) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_liebert_cooling.discovery_function(_section())) == [
        Service(item="Cooling Capacity (Primary)"),
        Service(item="Cooling Capacity (Secondary)"),
    ]


def test_checks() -> None:
    assert list(
        check_plugin_liebert_cooling.check_function(
            "Cooling Capacity (Primary)", {"min_capacity": (45, 40)}, _section()
        )
    ) == [
        Result(state=State.WARN, summary="42.00 % (warn/crit below 45.00 %/40.00 %)"),
        Metric("capacity_perc", 42.0),
    ]
