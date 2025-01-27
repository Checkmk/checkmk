#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.liebert.agent_based.lib import Section
from cmk.plugins.liebert.agent_based.liebert_reheating import (
    check_plugin_liebert_reheating,
    snmp_section_liebert_reheating,
)


def _section() -> Section[float]:
    assert (
        section := snmp_section_liebert_reheating.parse_function(
            [
                [
                    ["Reheating", "81.3", "%"],
                    ["This value ignored", "21.1", "deg C"],
                ]
            ]
        )
    ) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_liebert_reheating.discovery_function(_section())) == [
        Service(),
    ]


def test_checks() -> None:
    assert list(
        check_plugin_liebert_reheating.check_function({"levels": (80, 90)}, _section())
    ) == [
        Result(state=State.WARN, summary="81.30 % (warn/crit at 80.00 %/90.00 %)"),
        Metric("fan_perc", 81.3, levels=(80, 90)),
    ]
