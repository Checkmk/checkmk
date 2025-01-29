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
                ["1.6", "Pumpe 0 RZ4", "Kaeltepark RZ4", "2"],
                ["2.5", "Pumpe 1 RZ4", "Kaeltepark RZ4", "1"],
                ["2.6", "Pumpe 2 RZ4", "Kaeltepark RZ4", "3"],
            ],
            {
                "Pumpe 0 RZ4 1.6": Data(
                    location="Kaeltepark RZ4", state=("Open low mem", State.OK)
                ),
                "Pumpe 1 RZ4 2.5": Data(
                    location="Kaeltepark RZ4", state=("Closed high mem", State.CRIT)
                ),
                "Pumpe 2 RZ4 2.6": Data(location="Kaeltepark RZ4", state=("Disabled", State.WARN)),
            },
        ),
        (
            [["1.6", "Leckagekontrolle-RZ4", "Kaeltepark RZ4", "25"]],
            {
                "Leckagekontrolle-RZ4 1.6": Data(
                    location="Kaeltepark RZ4",
                    state=("unknown[25]", State.UNKNOWN),
                ),
            },
        ),
        (
            [["1.6", "Pumpe 1", "Kaeltepark RZ4", "3"]],
            {"Pumpe 1 1.6": Data(location="Kaeltepark RZ4", state=("Disabled", State.WARN))},
        ),
        ([], {}),
    ],
)
def test_apc_netbotz_drycontact_parse(info: StringTable, expected: Mapping[str, object]) -> None:
    assert parse_apc_netbotz_drycontact(info) == expected


@pytest.mark.parametrize(
    "item, data, expected",
    [
        (
            "Pumpe 1",
            {"Pumpe 1": Data(location="Kaeltepark", state=("Open low mem", State.OK))},
            Result(state=State.OK, summary="[Kaeltepark] State: Open low mem"),
        ),
        (
            "Pumpe 2",
            {"Pumpe 2": Data(location="Waermepark", state=("Closed high mem", State.CRIT))},
            Result(state=State.CRIT, summary="[Waermepark] State: Closed high mem"),
        ),
        (
            "Pumpe 3",
            {"Pumpe 3": Data(location="Kaeltepark", state=("Disabled", State.WARN))},
            Result(state=State.WARN, summary="[Kaeltepark] State: Disabled"),
        ),
        (
            "Pumpe 4",
            {"Pumpe 4": Data(location="Kaeltepark", state=("Not applicable", State.UNKNOWN))},
            Result(state=State.UNKNOWN, summary="[Kaeltepark] State: Not applicable"),
        ),
        (
            "Pumpe 5",
            {"Pumpe 5": Data(location="Kaeltepark", state=("unknown[5]", State.UNKNOWN))},
            Result(state=State.UNKNOWN, summary="[Kaeltepark] State: unknown[5]"),
        ),
        (
            "Pumpe without location",
            {"Pumpe without location": Data(location="", state=("unknown[5]", State.UNKNOWN))},
            Result(state=State.UNKNOWN, summary="State: unknown[5]"),
        ),
    ],
)
def test_apc_netbotz_drycontact_check(
    item: str,
    data: Mapping[str, Data],
    expected: Result,
) -> None:
    assert list(check_apc_netbotz_drycontact(item, data)) == [expected]
