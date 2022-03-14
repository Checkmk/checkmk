#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.iis_app_pool_state import (
    check_iis_app_pool_state,
    DefaultCheckParameters,
    IisAppPoolState,
)


@pytest.mark.parametrize(
    "item,section,params,results",
    [
        (
            "app",
            dict(app=IisAppPoolState.Initialized),
            DefaultCheckParameters,
            [
                Result(state=State.WARN, summary="State: Initialized"),
            ],
        ),
        (
            "app",
            dict(app=IisAppPoolState.ShutdownPending),
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
            dict(app=IisAppPoolState.Running),
            dict(state_mapping={"Running": State.CRIT.value}),
            [
                Result(state=State.CRIT, summary="State: Running"),
            ],
        ),
        (
            "app",
            dict(app=IisAppPoolState.Running),
            dict(state_mapping={}),
            [
                Result(state=State.CRIT, summary="State: Running"),
            ],
        ),
        (
            "app",
            dict(app=IisAppPoolState.Running),
            {},
            [
                Result(state=State.CRIT, summary="State: Running"),
            ],
        ),
    ],
)
def test_check_iis_app_pool_state(item, section, params, results):
    assert list(check_iis_app_pool_state(item, params, section)) == results
