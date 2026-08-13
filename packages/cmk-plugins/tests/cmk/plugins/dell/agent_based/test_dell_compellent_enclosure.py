#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.dell.agent_based.dell_compellent_enclosure import (
    check_dell_compellent_enclosure,
    parse_dell_compellent_enclosure,
)

_STRING_TABLE: StringTable = [
    ["1", "1", "", "TYP", "MODEL", "TAG"],
    ["2", "999", "", "TYP", "MODEL", "TAG"],
    ["3", "1", "ATTENTION", "TYP", "MODEL", "TAG"],
    ["4", "999", "ATTENTION", "TYP", "MODEL", "TAG"],
    ["10", "2", "KAPUTT", "TYP", "MODEL", "TAG"],
]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "1",
            [
                Result(state=State.OK, summary="Status: UP"),
                Result(state=State.OK, summary="Model: MODEL, Type: TYP, Service-Tag: TAG"),
            ],
        ),
        (
            "2",
            [
                Result(state=State.UNKNOWN, summary="Status: unknown[999]"),
                Result(state=State.OK, summary="Model: MODEL, Type: TYP, Service-Tag: TAG"),
            ],
        ),
        (
            "3",
            [
                Result(state=State.OK, summary="Status: UP"),
                Result(state=State.OK, summary="Model: MODEL, Type: TYP, Service-Tag: TAG"),
                Result(state=State.OK, summary="State Message: ATTENTION"),
            ],
        ),
        (
            "4",
            [
                Result(state=State.UNKNOWN, summary="Status: unknown[999]"),
                Result(state=State.OK, summary="Model: MODEL, Type: TYP, Service-Tag: TAG"),
                Result(state=State.UNKNOWN, summary="State Message: ATTENTION"),
            ],
        ),
        (
            "10",
            [
                Result(state=State.CRIT, summary="Status: DOWN"),
                Result(state=State.OK, summary="Model: MODEL, Type: TYP, Service-Tag: TAG"),
                Result(state=State.CRIT, summary="State Message: KAPUTT"),
            ],
        ),
    ],
)
def test_check_dell_compellent_enclosure(
    item: str,
    expected_results: Sequence[Result],
) -> None:
    parsed = parse_dell_compellent_enclosure(_STRING_TABLE)
    assert list(check_dell_compellent_enclosure(item, parsed)) == expected_results
