#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence, Tuple, TypedDict, Union

import pytest

from tests.testlib import Check

from cmk.base.plugins.agent_based.sentry_pdu import PDU

pytestmark = pytest.mark.checks

_SECTION = {
    "TowerA_InfeedA": PDU(state="on", power=1097),
    "TowerA_InfeedB": PDU(state="on", power=261),
    "TowerA_InfeedC": PDU(state="on", power=0),
    "TowerB_InfeedA": PDU(state="on", power=665),
    "TowerB_InfeedB": PDU(state="unknown", power=203),
    "TowerB_InfeedC": PDU(state="on", power=0),
}


def test_inventory_sentry_pdu() -> None:
    assert list(Check("sentry_pdu").run_discovery(_SECTION)) == [
        (
            "TowerA_InfeedA",
            {"discovered_state": "on"},
        ),
        (
            "TowerA_InfeedB",
            {"discovered_state": "on"},
        ),
        (
            "TowerA_InfeedC",
            {"discovered_state": "on"},
        ),
        (
            "TowerB_InfeedA",
            {"discovered_state": "on"},
        ),
        (
            "TowerB_InfeedB",
            {"discovered_state": "unknown"},
        ),
        (
            "TowerB_InfeedC",
            {"discovered_state": "on"},
        ),
    ]


class CombinedParams(TypedDict, total=False):
    required_state: str
    discovered_state: str


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "TowerA_InfeedA",
            {
                "discovered_state": "on",
            },
            [
                (0, "Status: on"),
                (0, "Power: 1097 Watt", [("power", 1097)]),
            ],
            id="discovered params, ok",
        ),
        pytest.param(
            "TowerA_InfeedA",
            {
                "discovered_state": "off",
            },
            [
                (2, "Status: on"),
                (0, "Power: 1097 Watt", [("power", 1097)]),
            ],
            id="discovered params, not ok",
        ),
        pytest.param(
            "TowerA_InfeedA",
            {
                "discovered_state": "on",
                "required_state": "on",
            },
            [
                (0, "Status: on"),
                (0, "Power: 1097 Watt", [("power", 1097)]),
            ],
            id="discovered and check params, ok",
        ),
        pytest.param(
            "TowerA_InfeedA",
            {
                "discovered_state": "on",
                "required_state": "off",
            },
            [
                (2, "Status: on"),
                (0, "Power: 1097 Watt", [("power", 1097)]),
            ],
            id="discovered and check params, not ok",
        ),
        pytest.param(
            "TowerB_InfeedB",
            {
                "discovered_state": "unknown",
            },
            [
                (3, "Status: unknown"),
                (0, "Power: 203 Watt", [("power", 203)]),
            ],
            id="unknown status",
        ),
    ],
)
def test_check_sentry_pdu(
    item: str,
    params: CombinedParams,
    expected_result: Sequence[Union[Tuple[int, str], Tuple[int, str, Tuple[str, int]]]],
) -> None:
    assert (
        list(
            Check("sentry_pdu").run_check(
                item,
                params,
                _SECTION,
            )
        )
        == expected_result
    )
