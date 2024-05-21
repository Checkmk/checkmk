#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import time_machine

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.liebert.agent_based.liebert_maintenance import (
    check_plugin_liebert_maintenance,
    Section,
    snmp_section_liebert_maintenance,
)


def _section() -> Section:
    assert (
        section := snmp_section_liebert_maintenance.parse_function(
            [
                [
                    ["Calculated Next Maintenance Month", "9"],
                    ["Calculated Next Maintenance Year", "2019"],
                ]
            ]
        )
    ) is not None
    return section


def test_discovery() -> None:
    assert list(check_plugin_liebert_maintenance.discovery_function(_section())) == [Service()]


def test_check() -> None:
    with time_machine.travel(datetime.datetime.fromtimestamp(1502247138, tz=ZoneInfo("CET"))):
        result = list(
            check_plugin_liebert_maintenance.check_function({"levels": (10, 5)}, _section())
        )

    assert result == [
        Result(state=State.OK, summary="Next maintenance: 9/2019"),
        Result(state=State.OK, summary="751 days"),
    ]
