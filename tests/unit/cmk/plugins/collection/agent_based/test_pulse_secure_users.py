#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.collection.agent_based import pulse_secure_users


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        (
            [[["172"]]],
            {"n_users": 172},
        ),
        (
            [[[""]]],
            {},
        ),
    ],
)
def test_parse_pulse_secure_users(
    string_table: Sequence[StringTable], expected_parsed_data: pulse_secure_users.Section | None
) -> None:
    assert pulse_secure_users.parse_pulse_secure_users(string_table) == expected_parsed_data


def test_check_pulse_secure_users() -> None:
    assert list(
        pulse_secure_users.check_pulse_secure_users(
            {"upper_number_of_users": None},
            {"n_users": 172},
        )
    ) == [
        Result(
            state=State.OK,
            summary="Pulse Secure users: 172",
            details="Pulse Secure users: 172",
        ),
        Metric(
            "current_users",
            172.0,
            levels=(None, None),
            boundaries=(None, None),
        ),
    ]


def test_cluster_check_pulse_secure_users() -> None:
    assert list(
        pulse_secure_users.cluster_check_pulse_secure_users(
            {"upper_number_of_users": None},
            {"node1": {"n_users": 20}, "node2": {"n_users": 30}},
        )
    ) == [
        Result(
            state=State.OK,
            notice="[node1]: Pulse Secure users: 20",
        ),
        Result(
            state=State.OK,
            notice="[node2]: Pulse Secure users: 30",
        ),
        Result(
            state=State.OK,
            summary="Pulse Secure users across cluster: 50",
            details="Pulse Secure users across cluster: 50",
        ),
        Metric(
            "current_users",
            50.0,
            levels=(None, None),
            boundaries=(None, None),
        ),
    ]
