#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.liebert.agent_based.liebert_bat_temp import (
    check_plugin_liebert_bat_temp,
    Section,
    snmp_section_liebert_bat_temp,
)


def _section() -> Section:
    assert (section := snmp_section_liebert_bat_temp.parse_function([[["37"]]])) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_liebert_bat_temp.discovery_function(_section())) == [
        Service(item="Battery")
    ]


def test_check() -> None:
    assert list(
        check_plugin_liebert_bat_temp.check_function(
            "Battery", {"levels": (30.0, 40.0)}, _section()
        )
    ) == [
        Metric("temp", 37.0, levels=(30.0, 40.0)),
        Result(
            state=State.WARN,
            summary="Temperature: 37 °C (warn/crit at 30.0 °C/40.0 °C)",
        ),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used user levels)",
        ),
    ]
