#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.f5_bigip_cluster_status import (
    check_f5_bigip_cluster_status,
    check_f5_bigip_cluster_status_v11_2,
    cluster_check_f5_bigip_cluster_status,
    cluster_check_f5_bigip_cluster_status_v11_2,
)
from cmk.base.plugins.agent_based.f5_bigip_cluster_status import (
    F5_BIGIP_CLUSTER_CHECK_DEFAULT_PARAMETERS as def_params,
)
from cmk.base.plugins.agent_based.f5_bigip_cluster_status import (
    parse_f5_bigip_cluster_status,
    parse_f5_bigip_vcmpfailover,
)


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        ([[["4"]]], 4),
    ],
)
def test_parse_f5_bigip_cluster_status(string_table, expected_parsed_data) -> None:
    assert parse_f5_bigip_cluster_status(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "arg,result",
    [
        ((def_params, 3), [Result(state=state.OK, summary="Node is active")]),
        ((def_params, 2), [Result(state=state.OK, summary="Node is active 2")]),
        ((def_params, 1), [Result(state=state.OK, summary="Node is active 1")]),
        ((def_params, 0), [Result(state=state.OK, summary="Node is standby")]),
    ],
)
def test_check_f5_bigip_cluster_status(arg, result) -> None:
    assert list(check_f5_bigip_cluster_status(arg[0], arg[1])) == result


@pytest.mark.parametrize(
    "arg,result",
    [
        ((def_params, 4), [Result(state=state.OK, summary="Node is active")]),
        (
            (
                {
                    "type": "active_standby",
                    "v11_2_states": {"0": 2, "1": 2, "2": 2, "3": 2, "4": 0},
                },
                4,
            ),
            [Result(state=state.OK, summary="Node is active")],
        ),
        ((def_params, 3), [Result(state=state.OK, summary="Node is standby")]),
        ((def_params, 2), [Result(state=state.CRIT, summary="Node is forced offline")]),
        ((def_params, 1), [Result(state=state.CRIT, summary="Node is offline")]),
        ((def_params, 0), [Result(state=state.UNKNOWN, summary="Node is unknown")]),
    ],
)
def test_check_f5_bigip_cluster_status_v11_2(arg, result) -> None:
    assert list(check_f5_bigip_cluster_status_v11_2(arg[0], arg[1])) == result


@pytest.mark.parametrize(
    "arg,result",
    [
        (
            (def_params, {"node1": 3}),
            [
                Result(state=state.OK, summary="Node [node1] is active"),
            ],
        ),
        (
            (def_params, {"node1": 0, "node2": 3}),
            [
                Result(state=state.OK, summary="Node [node1] is standby"),
                Result(state=state.OK, summary="Node [node2] is active"),
            ],
        ),
        (
            (def_params, {"node1": 3, "node2": 3}),
            [
                Result(state=state.CRIT, summary="More than 1 node is active: "),
                Result(state=state.OK, summary="Node [node1] is active"),
                Result(state=state.OK, summary="Node [node2] is active"),
            ],
        ),
    ],
)
def test_cluster_check_f5_bigip_cluster_status(arg, result) -> None:
    assert list(cluster_check_f5_bigip_cluster_status(arg[0], arg[1])) == result


@pytest.mark.parametrize(
    "arg,result",
    [
        (
            (def_params, {"node1": 4}),
            [
                Result(state=state.OK, summary="Node [node1] is active"),
            ],
        ),
        (
            (def_params, {"node1": 3, "node2": 4}),
            [
                Result(state=state.OK, summary="Node [node1] is standby"),
                Result(state=state.OK, summary="Node [node2] is active"),
            ],
        ),
        (
            (def_params, {"node1": 3, "node2": 3}),
            [
                Result(state=state.CRIT, summary="No active node found: "),
                Result(state=state.OK, summary="Node [node1] is standby"),
                Result(state=state.OK, summary="Node [node2] is standby"),
            ],
        ),
        (
            (def_params, {"node1": 4, "node2": 4}),
            [
                Result(state=state.CRIT, summary="More than 1 node is active: "),
                Result(state=state.OK, summary="Node [node1] is active"),
                Result(state=state.OK, summary="Node [node2] is active"),
            ],
        ),
    ],
)
def test_cluster_check_f5_bigip_cluster_status_v11_2(arg, result) -> None:
    assert list(cluster_check_f5_bigip_cluster_status_v11_2(arg[0], arg[1])) == result


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        ([[["0", "4"]]], 4),
        ([[["3", "4"]]], None),
    ],
)
def test_parse_f5_bigip_vcmpfailover(string_table, expected_parsed_data) -> None:
    assert parse_f5_bigip_vcmpfailover(string_table) == expected_parsed_data
