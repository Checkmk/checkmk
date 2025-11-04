#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.apc_netbotz_drycontact import (
    check_apc_netbotz_drycontact,
    Data,
    discover_apc_netbotz_drycontact,
    parse_apc_netbotz_drycontact,
)


@pytest.mark.parametrize(
    "parsed, expected",
    [
        (
            {
                "Pumpe 0": {
                    "location": "Kaeltepark RZ4",
                    "state": ("Closed high mem", 2),
                },
                "Pumpe 1": {
                    "location": "Kaeltepark RZ4",
                    "state": ("Closed high mem", 2),
                },
                "Pumpe 2": {
                    "location": "Kaeltepark RZ4",
                    "state": ("Closed high mem", 2),
                },
            },
            [Service(item="Pumpe 0"), Service(item="Pumpe 1"), Service(item="Pumpe 2")],
        )
    ],
)
def test_apc_netbotz_drycontact_inventory(
    parsed: Mapping[str, Data], expected: Sequence[object]
) -> None:
    assert list(discover_apc_netbotz_drycontact(parsed)) == expected


@pytest.mark.parametrize(
    "info, expected",
    [
        (
            [
                ["1.6", "Pumpe 0 RZ4", "Kaeltepark RZ4", "2", "1", "3"],
                ["2.5", "Pumpe 1 RZ4", "Kaeltepark RZ4", "1", "1", "3"],
                ["2.6", "Pumpe 2 RZ4", "Kaeltepark RZ4", "3", "1", "3"],
            ],
            {
                "Pumpe 0 RZ4 1.6": Data(
                    location="Kaeltepark RZ4",
                    state=("State: Open low mem [2] but expected Closed high mem [1]", State.CRIT),
                ),
                "Pumpe 1 RZ4 2.5": Data(
                    location="Kaeltepark RZ4",
                    state=("Normal state (Closed high mem [1])", State.OK),
                ),
                "Pumpe 2 RZ4 2.6": Data(
                    location="Kaeltepark RZ4",
                    state=("State: Disabled [3] but expected Closed high mem [1]", State.CRIT),
                ),
            },
        ),
        (
            # Test severity: not normal state, but only WARN because severity is Warning
            [["1.6", "Leckagekontrolle-RZ4", "Kaeltepark RZ4", "25", "2", "2"]],
            {
                "Leckagekontrolle-RZ4 1.6": Data(
                    location="Kaeltepark RZ4",
                    state=("State: unknown [25] but expected Open low mem [2]", State.WARN),
                ),
            },
        ),
        (
            # Test severity: not normal state, but OK because severity is Informational
            [["1.6", "Pumpe 1", "Kaeltepark RZ4", "3", "2", "1"]],
            {
                "Pumpe 1 1.6": Data(
                    location="Kaeltepark RZ4",
                    state=("State: Disabled [3] but expected Open low mem [2]", State.OK),
                )
            },
        ),
        ([], {}),
        (
            [
                ["1.6", "Pumpe 0 RZ4", "Kaeltepark RZ4", "2", "2", "3"],
                ["2.5", "Pumpe 1 RZ4", "Kaeltepark RZ4", "1", "2", "3"],
                ["2.6", "Pumpe 2 RZ4", "Kaeltepark RZ4", "3", "2", "4"],
            ],
            {
                "Pumpe 0 RZ4 1.6": Data(
                    location="Kaeltepark RZ4", state=("Normal state (Open low mem [2])", State.OK)
                ),
                "Pumpe 1 RZ4 2.5": Data(
                    location="Kaeltepark RZ4",
                    state=("State: Closed high mem [1] but expected Open low mem [2]", State.CRIT),
                ),
                "Pumpe 2 RZ4 2.6": Data(
                    location="Kaeltepark RZ4",
                    state=("State: Disabled [3] but expected Open low mem [2]", State.UNKNOWN),
                ),
            },
        ),
    ],
)
def test_apc_netbotz_drycontact_parse(info: StringTable, expected: Mapping[str, object]) -> None:
    assert parse_apc_netbotz_drycontact(info) == expected


@pytest.mark.parametrize(
    "item, data, expected",
    [
        (
            "Pumpe 1",
            {
                "Pumpe 1": Data(
                    location="Kaeltepark",
                    state=("State: Closed high mem [1] but expected Open low mem [2]", State.CRIT),
                )
            },
            Result(
                state=State.CRIT,
                summary="[Kaeltepark] State: Closed high mem [1] but expected Open low mem [2]",
            ),
        ),
        (
            "Pumpe 2",
            {
                "Pumpe 2": Data(
                    location="Waermepark",
                    state=("Normal state (Closed high mem [1])", State.OK),
                )
            },
            Result(
                state=State.OK,
                summary="[Waermepark] Normal state (Closed high mem [1])",
            ),
        ),
        (
            "Pumpe 3",
            {
                "Pumpe 3": Data(
                    location="Kaeltepark",
                    state=("State: Disabled [3] but expected Open low mem [2]", State.WARN),
                )
            },
            Result(
                state=State.WARN,
                summary="[Kaeltepark] State: Disabled [3] but expected Open low mem [2]",
            ),
        ),
        (
            "Pumpe 4",
            {
                "Pumpe 4": Data(
                    location="Kaeltepark",
                    state=("State: unknown [25] but expected Open low mem [2]", State.UNKNOWN),
                )
            },
            Result(
                state=State.UNKNOWN,
                summary="[Kaeltepark] State: unknown [25] but expected Open low mem [2]",
            ),
        ),
        (
            "Pumpe 5",
            {
                "Pumpe 5": Data(
                    location="Kaeltepark",
                    state=("State: unknown [5] but expected Open low mem [2]", State.UNKNOWN),
                )
            },
            Result(
                state=State.UNKNOWN,
                summary="[Kaeltepark] State: unknown [5] but expected Open low mem [2]",
            ),
        ),
        (
            "Pumpe without location",
            {
                "Pumpe without location": Data(
                    location="",
                    state=("State: unknown [5] but expected Open low mem [2]", State.UNKNOWN),
                )
            },
            Result(state=State.UNKNOWN, summary="State: unknown [5] but expected Open low mem [2]"),
        ),
    ],
)
def test_apc_netbotz_drycontact_check(
    item: str,
    data: Mapping[str, Data],
    expected: Result,
) -> None:
    assert list(check_apc_netbotz_drycontact(item, data)) == [expected]
