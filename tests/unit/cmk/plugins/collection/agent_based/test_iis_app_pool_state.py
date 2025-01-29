#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import CheckResult, Result, State
from cmk.plugins.collection.agent_based.iis_app_pool_state import (
    check_iis_app_pool_state,
    DefaultCheckParameters,
    IisAppPoolState,
    IisAppPoolStateCheckParams,
    Section,
)


@pytest.mark.parametrize(
    "item,section,params,results",
    [
        (
            "app",
            {"app": IisAppPoolState.Initialized},
            DefaultCheckParameters,
            [
                Result(state=State.WARN, summary="State: Initialized"),
            ],
        ),
        (
            "app",
            {"app": IisAppPoolState.ShutdownPending},
            DefaultCheckParameters,
            [
                Result(state=State.CRIT, summary="State: ShutdownPending"),
            ],
        ),
        (
            "app",
            {},
            DefaultCheckParameters,
            [
                Result(state=State.UNKNOWN, summary="app is unknown"),
            ],
        ),
        (
            "app",
            {"app": IisAppPoolState.Running},
            {"state_mapping": {"Running": State.CRIT.value}},
            [
                Result(state=State.CRIT, summary="State: Running"),
            ],
        ),
        (
            "app",
            {"app": IisAppPoolState.Running},
            {"state_mapping": {}},
            [
                Result(state=State.CRIT, summary="State: Running"),
            ],
        ),
        (
            "app",
            {"app": IisAppPoolState.Running},
            {},
            [
                Result(state=State.CRIT, summary="State: Running"),
            ],
        ),
    ],
)
def test_check_iis_app_pool_state(
    item: str, section: Section, params: IisAppPoolStateCheckParams, results: CheckResult
) -> None:
    assert list(check_iis_app_pool_state(item, params, section)) == results
