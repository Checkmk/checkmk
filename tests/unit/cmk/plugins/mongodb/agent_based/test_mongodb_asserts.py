#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, get_value_store, LevelsT, Metric, Result, Service, State
from cmk.plugins.mongodb.agent_based.asserts import (
    _check_mongodb_asserts,
    discover_mongodb_asserts,
    parse_mongodb_asserts,
)

_STRING_TABLE = [
    ["msg", "2000000000"],
    ["rollovers", "2000000000"],
    ["regular", "2000000000"],
    ["warning", "2000000000"],
    ["user", "2000000000"],
]


def test_discover_mongodb_asserts() -> None:
    assert list(discover_mongodb_asserts(parse_mongodb_asserts(_STRING_TABLE))) == [Service()]


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {},
            [
                Result(state=State.OK, summary="Msg asserts per sec: 1.21"),
                Metric("assert_msg", 1.2051717419264805),
                Result(state=State.OK, summary="Rollovers asserts per sec: 1.21"),
                Metric("assert_rollovers", 1.2051717419264805),
                Result(state=State.OK, summary="Regular asserts per sec: 1.21"),
                Metric("assert_regular", 1.2051717419264805),
                Result(state=State.OK, summary="Warning asserts per sec: 1.21"),
                Metric("assert_warning", 1.2051717419264805),
                Result(state=State.OK, summary="User asserts per sec: 1.21"),
                Metric("assert_user", 1.2051717419264805),
            ],
            id="All OK",
        ),
        pytest.param(
            {
                "msg_assert_rate": ("fixed", (1.0, 2.0)),
                "warning_assert_rate": ("fixed", (0.5, 1.0)),
            },
            [
                Result(
                    state=State.WARN, summary="Msg asserts per sec: 1.21 (warn/crit at 1.00/2.00)"
                ),
                Metric("assert_msg", 1.2051717419264805, levels=(1.0, 2.0)),
                Result(state=State.OK, summary="Rollovers asserts per sec: 1.21"),
                Metric("assert_rollovers", 1.2051717419264805),
                Result(state=State.OK, summary="Regular asserts per sec: 1.21"),
                Metric("assert_regular", 1.2051717419264805),
                Result(
                    state=State.CRIT,
                    summary="Warning asserts per sec: 1.21 (warn/crit at 0.50/1.00)",
                ),
                Metric("assert_warning", 1.2051717419264805, levels=(0.5, 1.0)),
                Result(state=State.OK, summary="User asserts per sec: 1.21"),
                Metric("assert_user", 1.2051717419264805),
            ],
            id="One WARN one CRIT",
        ),
    ],
)
def test_check_mongodb_asserts(
    params: Mapping[str, LevelsT[float]],
    expected_result: CheckResult,
) -> None:
    get_value_store().update(
        {
            "msg": (0, 0),
            "rollovers": (0, 0),
            "regular": (0, 0),
            "warning": (0, 0),
            "user": (0, 0),
        }
    )
    assert (
        list(
            _check_mongodb_asserts(
                params=params,
                section=parse_mongodb_asserts(_STRING_TABLE),
                now=1659514516,
            )
        )
        == expected_result
    )
