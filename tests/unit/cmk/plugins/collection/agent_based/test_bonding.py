#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v1 import Result, State
from cmk.agent_based.v1.type_defs import CheckResult
from cmk.plugins.collection.agent_based.bonding import _check_ieee_302_3ad_specific, check_bonding
from cmk.plugins.lib.bonding import Bond, Interface


@pytest.mark.parametrize(
    "params, status, result",
    [
        (
            {"ieee_302_3ad_agg_id_missmatch_state": 1},
            {
                "aggregator_id": "1",
                "interfaces": {
                    "ens1f0": {
                        "aggregator_id": "1",
                    },
                    "ens1f1": {
                        "aggregator_id": "1",
                    },
                },
            },
            [],
        ),
        (
            {"ieee_302_3ad_agg_id_missmatch_state": 1},
            {
                "aggregator_id": "1",
                "interfaces": {
                    "ens1f0": {
                        "aggregator_id": "1",
                    },
                    "ens1f1": {
                        "aggregator_id": "2",
                    },
                },
            },
            [
                Result(state=State.WARN, summary="Mismatching aggregator ID of ens1f1: 2"),
            ],
        ),
        (
            {"ieee_302_3ad_agg_id_missmatch_state": 1},
            {
                "interfaces": {
                    "ens1f0": {
                        "aggregator_id": "1",
                    },
                    "ens1f1": {
                        "aggregator_id": "1",
                    },
                },
            },
            [],
        ),
        (
            {"ieee_302_3ad_agg_id_missmatch_state": 2},
            {
                "interfaces": {
                    "ens1f0": {
                        "aggregator_id": "1",
                    },
                    "ens1f1": {
                        "aggregator_id": "2",
                    },
                },
            },
            [
                Result(state=State.CRIT, summary="Mismatching aggregator ID of ens1f1: 2"),
            ],
        ),
    ],
)
def test_check_ieee_302_3ad_specific(
    params: Mapping[str, object], status: Bond, result: CheckResult
) -> None:
    assert list(_check_ieee_302_3ad_specific(params, status)) == result


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "ieee_302_3ad_agg_id_missmatch_state": 1,
                "expect_active": "ignore",
            },
            [
                Result(state=State.OK, summary="Status: up"),
                Result(state=State.OK, summary="Mode: fault-tolerance"),
                Result(state=State.OK, summary="eth2/f8:4f:57:72:11:34 up"),
                Result(state=State.WARN, summary="eth3/f8:4f:57:72:11:36 down"),
            ],
            id="No parameter for number of interfaces",
        ),
        pytest.param(
            {
                "ieee_302_3ad_agg_id_missmatch_state": 1,
                "expect_active": "ignore",
                "expected_interfaces": {"expected_number": 3, "state": 2},
            },
            [
                Result(state=State.OK, summary="Status: up"),
                Result(state=State.OK, summary="Mode: fault-tolerance"),
                Result(state=State.OK, summary="eth2/f8:4f:57:72:11:34 up"),
                Result(state=State.WARN, summary="eth3/f8:4f:57:72:11:36 down"),
                Result(
                    state=State.CRIT,
                    summary="Unexpected number of interfaces (expected: 3, got: 2)",
                ),
            ],
            id="Not enough interfaces with CRIT state",
        ),
        pytest.param(
            {
                "ieee_302_3ad_agg_id_missmatch_state": 1,
                "expect_active": "ignore",
                "expected_interfaces": {"expected_number": 3, "state": 1},
            },
            [
                Result(state=State.OK, summary="Status: up"),
                Result(state=State.OK, summary="Mode: fault-tolerance"),
                Result(state=State.OK, summary="eth2/f8:4f:57:72:11:34 up"),
                Result(state=State.WARN, summary="eth3/f8:4f:57:72:11:36 down"),
                Result(
                    state=State.WARN,
                    summary="Unexpected number of interfaces (expected: 3, got: 2)",
                ),
            ],
            id="Not enough interfaces with WARN state",
        ),
        pytest.param(
            {
                "ieee_302_3ad_agg_id_missmatch_state": 1,
                "expect_active": "ignore",
                "expected_interfaces": {"expected_number": 2, "state": 1},
            },
            [
                Result(state=State.OK, summary="Status: up"),
                Result(state=State.OK, summary="Mode: fault-tolerance"),
                Result(state=State.OK, summary="eth2/f8:4f:57:72:11:34 up"),
                Result(state=State.WARN, summary="eth3/f8:4f:57:72:11:36 down"),
            ],
            id="Expected number of interfaces is equal to the actual number",
        ),
        pytest.param(
            {
                "ieee_302_3ad_agg_id_missmatch_state": 1,
                "expect_active": "ignore",
                "expected_interfaces": {"expected_number": 1, "state": 1},
            },
            [
                Result(state=State.OK, summary="Status: up"),
                Result(state=State.OK, summary="Mode: fault-tolerance"),
                Result(state=State.OK, summary="eth2/f8:4f:57:72:11:34 up"),
                Result(state=State.WARN, summary="eth3/f8:4f:57:72:11:36 down"),
            ],
            id="Number of interfaces is bigger than expected",
        ),
    ],
)
def test_check_interfaces_number(params: Mapping[str, Any], expected_result: list[Result]) -> None:
    input_section = {
        "bond0": Bond(
            status="up",
            mode="fault-tolerance",
            interfaces={
                "eth2": Interface(status="up", hwaddr="f8:4f:57:72:11:34", failures=1),
                "eth3": Interface(status="down", hwaddr="f8:4f:57:72:11:36", failures=0),
            },
            active="eth2",
            primary="None",
        )
    }

    result = list(
        check_bonding(
            "bond0",
            params,
            input_section,
        )
    )
    assert result == expected_result
