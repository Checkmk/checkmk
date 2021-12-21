#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based import pulse_secure_users
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state


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
def test_parse_pulse_secure_users(string_table, expected_parsed_data):
    assert pulse_secure_users.parse_pulse_secure_users(string_table) == expected_parsed_data


def test_check_pulse_secure_users():
    assert list(pulse_secure_users.check_pulse_secure_users({}, {"n_users": 172},)) == [
        Result(
            state=state.OK,
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


def test_cluster_check_pulse_secure_users():
    assert list(
        pulse_secure_users.cluster_check_pulse_secure_users(
            {},
            {"node1": {"n_users": 20}, "node2": {"n_users": 30}},
        )
    ) == [
        Result(
            state=state.OK,
            notice="[node1]: Pulse Secure users: 20",
        ),
        Result(
            state=state.OK,
            notice="[node2]: Pulse Secure users: 30",
        ),
        Result(
            state=state.OK,
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
