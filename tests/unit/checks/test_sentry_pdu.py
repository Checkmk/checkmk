#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence, Tuple, Union

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
    "TowerB_InfeedC": PDU(state="on", power=0)
}


def test_inventory_sentry_pdu() -> None:
    assert list(Check("sentry_pdu").run_discovery(_SECTION)) == [
        ("TowerA_InfeedA", "on"),
        ("TowerA_InfeedB", "on"),
        ("TowerA_InfeedC", "on"),
        ("TowerB_InfeedA", "on"),
        ("TowerB_InfeedB", "unknown"),
        ("TowerB_InfeedC", "on"),
    ]


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "TowerA_InfeedA",
            "on",
            [
                (0, "Status: on"),
                (0, "Power: 1097 Watt", [("power", 1097)]),
            ],
            id="discovered params, ok",
        ),
        pytest.param(
            "TowerA_InfeedA",
            "off",
            [
                (2, "Status: on"),
                (0, "Power: 1097 Watt", [("power", 1097)]),
            ],
            id="discovered params, not ok",
        ),
        # The following 2 configurations do not work correctly and will be fixed in the following
        # commits
        pytest.param(
            "TowerA_InfeedA",
            {"required_state": "on"},
            [
                (2, "Status: on"),
                (0, "Power: 1097 Watt", [("power", 1097)]),
            ],
            id="checks params, ok",
        ),
        pytest.param(
            "TowerA_InfeedA",
            {"required_state": "off"},
            [
                (2, "Status: on"),
                (0, "Power: 1097 Watt", [("power", 1097)]),
            ],
            id="checks params, not ok",
        ),
    ],
)
def test_check_sentry_pdu(
    item: str,
    params,  # we will type this parameter later
    expected_result: Sequence[Union[Tuple[int, str], Tuple[int, str, Tuple[str, int]]]],
) -> None:
    assert list(Check("sentry_pdu").run_check(
        item,
        params,
        _SECTION,
    )) == expected_result
