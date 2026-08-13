#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.dell.agent_based.dell_compellent_controller import (
    check_dell_compellent_controller,
    parse_dell_compellent_controller,
)

_STRING_TABLE = [
    ["1", "1", "Foo", "1.2.3.4", "Model"],
    ["2", "999", "Bar", "5.6.7.8", "Model"],
    ["10", "2", "Baz", "1.3.5.7", "Model"],
]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "1",
            [
                Result(state=State.OK, summary="Status: UP"),
                Result(state=State.OK, summary="Model: Model, Name: Foo, Address: 1.2.3.4"),
            ],
        ),
        (
            "2",
            [
                Result(state=State.UNKNOWN, summary="Status: unknown[999]"),
                Result(state=State.OK, summary="Model: Model, Name: Bar, Address: 5.6.7.8"),
            ],
        ),
        (
            "10",
            [
                Result(state=State.CRIT, summary="Status: DOWN"),
                Result(state=State.OK, summary="Model: Model, Name: Baz, Address: 1.3.5.7"),
            ],
        ),
    ],
)
def test_check_dell_compellent_controller(
    item: str,
    expected_results: Sequence[Result],
) -> None:
    parsed = parse_dell_compellent_controller(_STRING_TABLE)
    assert list(check_dell_compellent_controller(item, parsed)) == expected_results
