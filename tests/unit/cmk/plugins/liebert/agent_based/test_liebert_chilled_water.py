#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.liebert.agent_based.lib import SectionWithoutUnit
from cmk.plugins.liebert.agent_based.liebert_chilled_water import (
    check_plugin_liebert_chilled_water,
    snmp_section_liebert_chilled_water,
)


def _section() -> SectionWithoutUnit[str]:
    assert (
        section := snmp_section_liebert_chilled_water.parse_function(
            [
                [
                    [
                        "Supply Chilled Water Over Temp",
                        "Inactive Event",
                        "Chilled Water Control Valve Failure",
                        "Inactive Event",
                        "Supply Chilled Water Loss of Flow",
                        "Everything is on fire",
                    ]
                ]
            ]
        )
    ) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_liebert_chilled_water.discovery_function(_section())) == [
        Service(item="Supply Chilled Water Over Temp"),
        Service(item="Chilled Water Control Valve Failure"),
        Service(item="Supply Chilled Water Loss of Flow"),
    ]


def test_check_ok() -> None:
    assert list(
        check_plugin_liebert_chilled_water.check_function(
            "Supply Chilled Water Over Temp", _section()
        )
    ) == [
        Result(state=State.OK, summary="Normal"),
    ]


def test_check_crit() -> None:
    assert list(
        check_plugin_liebert_chilled_water.check_function(
            "Supply Chilled Water Loss of Flow", _section()
        )
    ) == [
        Result(state=State.CRIT, summary="Everything is on fire"),
    ]
