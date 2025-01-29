#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.liebert.agent_based.lib import SystemSection
from cmk.plugins.liebert.agent_based.liebert_system import (
    check_liebert_system,
    discover_liebert_system,
    parse_liebert_system,
)


@pytest.mark.parametrize(
    "string_table, result",
    [
        (
            [
                [
                    [
                        "System Status",
                        "Normal Operation",
                        "System Model Number",
                        "Liebert CRV",
                        "Unit Operating State",
                        "standby",
                        "Unit Operating State Reason",
                        "Reason Unknown",
                    ]
                ]
            ],
            {
                "System Model Number": "Liebert CRV",
                "System Status": "Normal Operation",
                "Unit Operating State": "standby",
                "Unit Operating State Reason": "Reason Unknown",
            },
        ),
        (
            [
                [
                    [
                        "System Status",
                        "Normal Operation",
                        "System Model Number",
                        "Liebert CRV",
                        "Unit Operating State",
                        "on",
                        "Unit Operating State Reason",
                        "Reason Unknown",
                    ]
                ]
            ],
            {
                "System Model Number": "Liebert CRV",
                "System Status": "Normal Operation",
                "Unit Operating State": "on",
                "Unit Operating State Reason": "Reason Unknown",
            },
        ),
    ],
)
def test_parse_liebert_system(string_table: list[StringTable], result: SystemSection) -> None:
    parsed = parse_liebert_system(string_table)
    assert parsed == result


@pytest.mark.parametrize(
    "section, result",
    [
        (
            {
                "System Model Number": "Liebert CRV",
                "System Status": "Normal Operation",
                "Unit Operating State": "standby",
                "Unit Operating State Reason": "Reason Unknown",
            },
            [Service(item="Liebert CRV")],
        ),
        (
            {
                "System Model Number": "Liebert CRV",
                "System Status": "Normal Operation",
                "Unit Operating State": "on",
                "Unit Operating State Reason": "Reason Unknown",
            },
            [Service(item="Liebert CRV")],
        ),
    ],
)
def test_discover_liebert_system(section: SystemSection, result: DiscoveryResult) -> None:
    discovered = list(discover_liebert_system(section))
    assert discovered == result


@pytest.mark.parametrize(
    "section, result",
    [
        (
            {
                "System Model Number": "Liebert CRV",
                "System Status": "Normal Operation",
                "Unit Operating State": "standby",
                "Unit Operating State Reason": "Reason Unknown",
            },
            [
                Result(
                    state=State.OK,
                    summary="System Model Number: Liebert CRV",
                    details="System Model Number: Liebert CRV",
                ),
                Result(
                    state=State.OK,
                    summary="System Status: Normal Operation",
                    details="System Status: Normal Operation",
                ),
                Result(
                    state=State.OK,
                    summary="Unit Operating State: standby",
                    details="Unit Operating State: standby",
                ),
                Result(
                    state=State.OK,
                    summary="Unit Operating State Reason: Reason Unknown",
                    details="Unit Operating State Reason: Reason Unknown",
                ),
            ],
        ),
        (
            {
                "System Model Number": "Liebert CRV",
                "System Status": "Normal Operation",
                "Unit Operating State": "on",
                "Unit Operating State Reason": "Reason Unknown",
            },
            [
                Result(
                    state=State.OK,
                    summary="System Model Number: Liebert CRV",
                    details="System Model Number: Liebert CRV",
                ),
                Result(
                    state=State.OK,
                    summary="System Status: Normal Operation",
                    details="System Status: Normal Operation",
                ),
                Result(
                    state=State.OK,
                    summary="Unit Operating State: on",
                    details="Unit Operating State: on",
                ),
                Result(
                    state=State.OK,
                    summary="Unit Operating State Reason: Reason Unknown",
                    details="Unit Operating State Reason: Reason Unknown",
                ),
            ],
        ),
    ],
)
def test_check_liebert_system(section: SystemSection, result: CheckResult) -> None:
    checked = list(check_liebert_system("Liebert CRV", section))
    assert checked == result
