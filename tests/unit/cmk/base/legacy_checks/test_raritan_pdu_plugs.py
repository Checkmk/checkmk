#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import TypedDict

import pytest

from .checktestlib import Check

pytestmark = pytest.mark.checks

_SECTION = {
    "1": {"outlet_name": "outlet1", "state": "on"},
    "2": {"outlet_name": "outlet2", "state": "off"},
    "3": {"outlet_name": "", "state": "unknown"},
    "4": {"outlet_name": "", "state": "on"},
    "5": {"outlet_name": "", "state": "on"},
    "6": {"outlet_name": "", "state": "on"},
    "7": {"outlet_name": "broken", "state": "unknown"},
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


def test_discover_raritan_pdu_plugs() -> None:
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
    ]


class CombinedParams(TypedDict, total=False):
    required_state: str
    discovered_state: str


@pytest.mark.parametrize(
    "item, params, expected_result",
    [
        pytest.param(
            "1",
            {"discovered_state": "on", "required_state": None},
            [
                (0, "outlet1"),
                (0, "Status: on"),
            ],
            id="using discovered params since required state not set - match (OK)",
        ),
        pytest.param(
            "1",
            {"discovered_state": "off", "required_state": None},
            [
                (0, "outlet1"),
                (2, "Status: on (expected: off)"),
            ],
            id="using discovered params since required state not set - mismatch (CRIT)",
        ),
        pytest.param(
            "1",
            {"discovered_state": "off", "required_state": "on"},
            [
                (0, "outlet1"),
                (0, "Status: on"),
            ],
            id="required state is set and takes priority over discovered - match (OK)",
        ),
        pytest.param(
            "1",
            {"discovered_state": "on", "required_state": "off"},
            [
                (0, "outlet1"),
                (2, "Status: on (expected: off)"),
            ],
            id="required state is set and takes priority over discovered - mismatch (CRIT)",
        ),
        pytest.param(
            "5",
            {"discovered_state": "on", "required_state": "on"},
            [
                (0, "Status: on"),
            ],
            id="item without defined outlet_name still works",
        ),
        pytest.param(
            "7",
            {"discovered_state": "unknown", "required_state": None},
            [
                (0, "broken"),
                (0, "Status: unknown"),
            ],
            id="unknown status matches discovered state",
        ),
        pytest.param(
            "7",
            {"discovered_state": "unknown", "required_state": "off"},
            [
                (0, "broken"),
                (2, "Status: unknown (expected: off)"),
            ],
            id="unknown status does not match required state",
        ),
    ],
)
def test_check_raritan_pdu_plugs(
    item: str,
    params: CombinedParams,
    expected_result: Sequence[tuple[int, str]],
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
