#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.audiocodes.agent_based.module_names import (
    parse_module_names,
)
from cmk.plugins.audiocodes.agent_based.temperature import (
    check_audiocodes_temperature,
    discover_audiocodes_temperature,
    parse_audiocodes_temperature,
)
from cmk.plugins.lib.temperature import TempParamDict

_STRING_TABLE_TEMPERATURE = [
    ["67387393", "-1"],
    ["67907585", "26"],
]
_STRING_TABLE_MODULE_NAMES = [
    ["67387393", "Mediant-4000 Media Processing Module"],
    ["67641344", "Mediant-4000 Slot"],
    ["67903488", "Mediant-4000 Slot"],
    ["67907585", "Mediant-4000 CPU Module"],
]


def test_discovery_function() -> None:
    section_temperature = parse_audiocodes_temperature(_STRING_TABLE_TEMPERATURE)
    section_module_names = parse_module_names(_STRING_TABLE_MODULE_NAMES)
    assert list(discover_audiocodes_temperature(section_module_names, section_temperature)) == [
        Service(item="Mediant-4000 Media Processing Module 67387393"),
        Service(item="Mediant-4000 CPU Module 67907585"),
    ]


@pytest.mark.parametrize(
    "item, params, expected",
    [
        pytest.param(
            "not_found",
            {},
            [],
            id="Item not found",
        ),
        pytest.param(
            "Mediant-4000 Media Processing Module 67387393",
            {},
            [
                Result(state=State.OK, summary="Temperature is not available"),
            ],
            id="Not applicable temperature",
        ),
        pytest.param(
            "Mediant-4000 CPU Module 67907585",
            {"levels": (22.0, 25.0)},
            [
                Metric("temp", 26.0, levels=(22.0, 25.0)),
                Result(
                    state=State.CRIT, summary="Temperature: 26.0 °C (warn/crit at 22.0 °C/25.0 °C)"
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used user levels)",
                ),
            ],
            id="CRIT level temperature",
        ),
    ],
)
def test_check_function(
    item: str,
    params: TempParamDict,
    expected: CheckResult,
) -> None:
    section_temperature = parse_audiocodes_temperature(_STRING_TABLE_TEMPERATURE)
    section_module_names = parse_module_names(_STRING_TABLE_MODULE_NAMES)
    assert (
        list(check_audiocodes_temperature(item, params, section_module_names, section_temperature))
        == expected
    )
