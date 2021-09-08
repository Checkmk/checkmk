#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Sequence, Tuple, TypedDict

import pytest

from tests.testlib import Check

pytestmark = pytest.mark.checks

_SECTION = {
    "1": {"outlet_name": "outlet1", "state": (0, "on")},
    "2": {"outlet_name": "outlet2", "state": (2, "off")},
    "3": {"outlet_name": "", "state": (0, "closed")},
    "4": {"outlet_name": "", "state": (0, "on")},
    "5": {"outlet_name": "", "state": (0, "on")},
    "6": {"outlet_name": "", "state": (0, "on")},
    "7": {"outlet_name": "broken", "state": (3, "unknown")},
}


def test_parse_raritan_pdu_plugs() -> None:
    assert (
        Check("raritan_pdu_plugs").run_parse(
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


def test_inventory_raritan_pdu_plugs() -> None:
    assert list(Check("raritan_pdu_plugs").run_discovery(_SECTION)) == [
        (
            "1",
            {"discovered_state": "on"},
        ),
        (
            "2",
            {"discovered_state": "off"},
        ),
        (
            "3",
            {"discovered_state": "closed"},
        ),
        (
            "4",
            {"discovered_state": "on"},
        ),
        (
            "5",
            {"discovered_state": "on"},
        ),
        (
            "6",
            {"discovered_state": "on"},
        ),
        (
            "7",
            {"discovered_state": "unknown"},
        ),
    ]


class CombinedParams(TypedDict, total=False):
    required_state: str
    discovered_state: str


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "1",
            {"discovered_state": "on"},
            [
                (0, "outlet1"),
                (0, "Status: on"),
            ],
            id="discovered params, ok",
        ),
        pytest.param(
            "1",
            {"discovered_state": "above upper warning"},
            [
                (0, "outlet1"),
                (0, "Status: on"),
                (2, "Expected: above upper warning"),
            ],
            id="discovered params, not ok",
        ),
        pytest.param(
            "1",
            {
                "discovered_state": "on",
                "required_state": "on",
            },
            [
                (0, "outlet1"),
                (0, "Status: on"),
            ],
            id="discovered and check params, ok",
        ),
        pytest.param(
            "1",
            {
                "discovered_state": "on",
                "required_state": "off",
            },
            [
                (0, "outlet1"),
                (0, "Status: on"),
                (2, "Expected: off"),
            ],
            id="discovered and check params, not ok",
        ),
        pytest.param(
            "5",
            {"discovered_state": "on"},
            [
                (0, "Status: on"),
            ],
            id="without outlet_name",
        ),
        pytest.param(
            "7",
            {
                "discovered_state": "unknown",
                "required_state": "off",
            },
            [
                (0, "broken"),
                (3, "Status: unknown"),
                (2, "Expected: off"),
            ],
            id="unknown status",
        ),
    ],
)
def test_check_raritan_pdu_plugs(
    item: str,
    params: CombinedParams,
    expected_result: Sequence[Tuple[int, str]],
) -> None:
    assert (
        list(
            Check("raritan_pdu_plugs").run_check(
                item,
                params,
                _SECTION,
            )
        )
        == expected_result
    )
