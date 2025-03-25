#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.liebert.agent_based.lib import Section, SystemSection
from cmk.plugins.liebert.agent_based.liebert_humidity_air import (
    check_liebert_humidity_air,
    discover_liebert_humidity_air,
    parse_liebert_humidity_air,
)

ParsedSection = Section[str]

STRING_TABLE = [
    [
        [
            "Return Humidity",
            "36.5",
            "% RH",
            "Cigar Humidity",
            "Unavailable",
            "% RH",
        ]
    ]
]

PARAMETERS = {
    "levels": (50, 55),
    "levels_lower": (10, 15),
}

PARSED_SECTION = {
    "Return Humidity": ("36.5", "% RH"),
    "Cigar Humidity": ("Unavailable", "% RH"),
}

PARSED_EXTRA_SECTION = {
    "System Model Number": "Liebert CRV",
    "System Status": "Normal Operation",
    "Unit Operating State": "standby",
    "Unit Operating State Reason": "Reason Unknown",
}


@pytest.mark.parametrize(
    "string_table, result",
    [
        (
            STRING_TABLE,
            PARSED_SECTION,
        ),
    ],
)
def test_parse_liebert_humidity_air(string_table: list[StringTable], result: ParsedSection) -> None:
    parsed = parse_liebert_humidity_air(string_table)
    assert parsed == result


@pytest.mark.parametrize(
    "section, extra_section, result",
    [
        (
            PARSED_SECTION,
            PARSED_EXTRA_SECTION,
            [Service(item="Return")],
        )
    ],
)
def test_discover_liebert_humidity_air(
    section: ParsedSection | None, extra_section: SystemSection | None, result: DiscoveryResult
) -> None:
    discovered = list(discover_liebert_humidity_air(section, extra_section))
    assert discovered == result


@pytest.mark.parametrize(
    "item, params, section, extra_section, result",
    [
        (
            "Return",
            PARAMETERS,
            PARSED_SECTION,
            PARSED_EXTRA_SECTION,
            [
                Result(state=State.OK, summary="36.50 % RH"),
                Metric(name="humidity", value=36.5, levels=(50.0, 55.0), boundaries=(0.0, None)),
            ],
        ),
        (
            # Item 'Cigar' is not discovered in the discovery function. However, it is tested in this check function
            # in order to test whether the check handles the item correctly when it changes its status from 'on' to
            # 'standby'.
            "Cigar",
            PARAMETERS,
            PARSED_SECTION,
            PARSED_EXTRA_SECTION,
            [
                Result(
                    state=State.OK,
                    summary="Unit is in standby (unavailable)",
                    details="Unit is in standby (unavailable)",
                ),
            ],
        ),
    ],
)
def test_check_liebert_humidity_air(
    item: str,
    params: Mapping[str, object],
    section: ParsedSection | None,
    extra_section: SystemSection | None,
    result: CheckResult,
) -> None:
    checked = list(check_liebert_humidity_air(item, params, section, extra_section))
    assert checked == result
