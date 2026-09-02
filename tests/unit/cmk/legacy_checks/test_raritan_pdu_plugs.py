#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.legacy_checks.raritan_pdu_plugs import (
    check_raritan_pdu_plugs,
    CombinedParams,
    discover_raritan_pdu_plugs,
    parse_raritan_pdu_plugs,
    Plug,
)

_SECTION = {
    "1": Plug(outlet_name="outlet1", state="on"),
    "2": Plug(outlet_name="outlet2", state="off"),
    "3": Plug(outlet_name="", state="unknown"),
    "4": Plug(outlet_name="", state="on"),
    "5": Plug(outlet_name="", state="on"),
    "6": Plug(outlet_name="", state="on"),
    "7": Plug(outlet_name="broken", state="unknown"),
}


def test_parse_raritan_pdu_plugs() -> None:
    assert (
        parse_raritan_pdu_plugs(
            [
                ["1", "outlet1", "7"],
                ["2", "outlet2", "8"],
                ["3", "", "1"],
                ["4", "", "7"],
                ["5", "", "7"],
                ["6", "", "7"],
                ["7", "broken", "45"],
            ]
        )
        == _SECTION
    )


def test_discover_raritan_pdu_plugs() -> None:
    assert list(discover_raritan_pdu_plugs(_SECTION)) == [
        Service(item="1", parameters={"discovered_state": "on"}),
        Service(item="2", parameters={"discovered_state": "off"}),
        Service(item="4", parameters={"discovered_state": "on"}),
        Service(item="5", parameters={"discovered_state": "on"}),
        Service(item="6", parameters={"discovered_state": "on"}),
    ]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "1",
            {"discovered_state": "on", "required_state": None},
            [
                Result(state=State.OK, summary="outlet1"),
                Result(state=State.OK, summary="Status: on"),
            ],
            id="using discovered params since required state not set - match (OK)",
        ),
        pytest.param(
            "1",
            {"discovered_state": "off", "required_state": None},
            [
                Result(state=State.OK, summary="outlet1"),
                Result(state=State.CRIT, summary="Status: on (expected: off)"),
            ],
            id="using discovered params since required state not set - mismatch (CRIT)",
        ),
        pytest.param(
            "1",
            {"discovered_state": "off", "required_state": "on"},
            [
                Result(state=State.OK, summary="outlet1"),
                Result(state=State.OK, summary="Status: on"),
            ],
            id="required state is set and takes priority over discovered - match (OK)",
        ),
        pytest.param(
            "1",
            {"discovered_state": "on", "required_state": "off"},
            [
                Result(state=State.OK, summary="outlet1"),
                Result(state=State.CRIT, summary="Status: on (expected: off)"),
            ],
            id="required state is set and takes priority over discovered - mismatch (CRIT)",
        ),
        pytest.param(
            "5",
            {"discovered_state": "on", "required_state": "on"},
            [
                Result(state=State.OK, summary="Status: on"),
            ],
            id="item without defined outlet_name still works",
        ),
        pytest.param(
            "7",
            {"discovered_state": "unknown", "required_state": None},
            [
                Result(state=State.OK, summary="broken"),
                Result(state=State.OK, summary="Status: unknown"),
            ],
            id="unknown status matches discovered state",
        ),
        pytest.param(
            "7",
            {"discovered_state": "unknown", "required_state": "off"},
            [
                Result(state=State.OK, summary="broken"),
                Result(state=State.CRIT, summary="Status: unknown (expected: off)"),
            ],
            id="unknown status does not match required state",
        ),
    ],
)
def test_check_raritan_pdu_plugs(
    item: str,
    params: CombinedParams,
    expected_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_raritan_pdu_plugs(
                item,
                params,
                _SECTION,
            )
        )
        == expected_result
    )
