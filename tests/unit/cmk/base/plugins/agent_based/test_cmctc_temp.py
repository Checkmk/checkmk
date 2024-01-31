#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.legacy_checks.cmctc import parse_cmctc_temp, Section, Sensor

from cmk.agent_based.v2.type_defs import StringTable

_INF = float("-inf")


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param(
            [
                [
                    ["1", "30", "4", "0", "130", "10", "70", "Power (PSM)"],
                    ["2", "31", "4", "1", "0", "0", "0", "State (PSM)"],
                    ["3", "32", "4", "2", "0", "0", "0", "Position (PSM)"],
                    ["4", "30", "4", "0", "130", "10", "70", "Power (PSM)"],
                    ["5", "31", "4", "1", "0", "0", "0", "State (PSM)"],
                    ["6", "32", "4", "1", "0", "0", "0", "Position (PSM)"],
                    ["7", "30", "4", "3", "130", "10", "70", "Power (PSM)"],
                    ["8", "31", "4", "1", "0", "0", "0", "State (PSM)"],
                    ["9", "32", "4", "1", "0", "0", "0", "Position (PSM)"],
                ],
                [
                    ["1", "10", "4", "21", "65", "10", "35", "Temperatursensor"],
                    ["2", "1", "1", "0", "0", "0", "0", "nicht verfuegbar"],
                    ["", "", "", "", "", "", "", "Luefter"],
                ],
                [
                    ["1", "4", "4", "1", "0", "0", "0", "Access sensor"],
                    ["2", "1", "1", "0", "0", "0", "0", "nicht verfuegbar"],
                    ["3", "1", "1", "0", "0", "0", "0", "nicht verfuegbar"],
                    ["4", "10", "4", "24", "65", "10", "55", "Temperatursensor"],
                ],
                [],
            ],
            {
                "4.1": Sensor(status=4, reading=21, levels=(35.0, 65.0), levels_lower=(10.0, _INF)),
                "5.4": Sensor(status=4, reading=24, levels=(55.0, 65.0), levels_lower=(10.0, _INF)),
            },
            marks=pytest.mark.xfail,
        ),
    ],
)
def test_parse_cmctc_temp(string_table: list[StringTable], expected: Section) -> None:
    """An SNMP tree can be empty."""

    assert parse_cmctc_temp(string_table) == expected
