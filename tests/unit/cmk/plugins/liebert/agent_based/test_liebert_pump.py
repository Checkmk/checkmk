#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.liebert.agent_based.lib import Section
from cmk.plugins.liebert.agent_based.liebert_pump import (
    check_plugin_liebert_pump,
    snmp_section_liebert_pump,
)


def _section() -> Section[float]:
    assert (
        section := snmp_section_liebert_pump.parse_function(
            [
                [
                    ["Pump Hours", "3423", "hr"],
                    ["Pump Hours", "1", "hr"],
                    ["Pump Hours Threshold", "32", "hr"],
                    ["Pump Hours Threshold", "32", "hr"],
                ]
            ]
        )
    ) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_liebert_pump.discovery_function(_section())) == [
        Service(item="Pump Hours"),
        Service(item="Pump Hours 2"),
    ]


def test_check() -> None:
    assert list(check_plugin_liebert_pump.check_function("Pump Hours", _section())) == [
        Result(
            state=State.CRIT,
            summary="3423.00 hr (warn/crit at 32.00 hr/32.00 hr)",
        ),
    ]


def test_check_no_threshold() -> None:
    assert list(check_plugin_liebert_pump.check_function("Pump Hours 2", _section())) == [
        Result(
            state=State.OK,
            summary="1.00 hr",
        ),
    ]
