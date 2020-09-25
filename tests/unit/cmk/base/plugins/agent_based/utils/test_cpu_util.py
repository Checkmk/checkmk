#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict
import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State as state
from cmk.base.plugins.agent_based.utils import cpu_util

pytestmark = pytest.mark.checks


def test_check_cpu_util():
    """
    Test a quite streight forward case. Nothing in particular, just to have at least any test.
    """

    value_store: Dict[str, Any] = {}

    assert list(
        cpu_util.check_cpu_util(
            value_store=value_store,
            util=123.0,
            params={
                "average": 3.,
                "levels": (80.0, 90.0),
                "levels_single": (12.0, 13.0),
            },
            this_time=0.,  # Jan 1 1970 (who cares)
            cores=[
                ('my_core', 12.0),
                ('your_core', 42.0),
            ],
            perf_max=200.0,
        )) == [
            Metric('util', 123.0, levels=(80.0, 90.0), boundaries=(0.0, 200.0)),
            Result(
                state=state.CRIT,
                summary='Total CPU (3min average): 123% (warn/crit at 80.0%/90.0%)',
            ),
            Metric('util_average', 123.0, levels=(80.0, 90.0)),
            Result(
                state=state.WARN,
                summary='Core my_core: 12.0% (warn/crit at 12.0%/13.0%)',
            ),
            Result(
                state=state.CRIT,
                summary='Core your_core: 42.0% (warn/crit at 12.0%/13.0%)',
            ),
        ]


def test_cpu_util_time():

    value_store: Dict[str, Any] = {}

    # over threshold for the first time
    assert not list(
        cpu_util.cpu_util_time(
            this_time=23.,
            core="my_core",
            perc=42.0,
            threshold=40.0,
            levels=(5., 10.),
            value_store=value_store,
        ))

    # over threshold for more that warn
    assert list(
        cpu_util.cpu_util_time(
            this_time=30.0,
            core="my_core",
            perc=42.0,
            threshold=40.0,
            levels=(5., 10.),
            value_store=value_store,
        )
    ) == [
        Result(
            state=state.WARN,
            summary='my_core is under high load for: 7 seconds (warn/crit at 5 seconds/10 seconds)',
        ),
    ]

    assert not list(
        cpu_util.cpu_util_time(
            this_time=34.0,
            core="my_core",
            perc=39.0,  # <--------- back to OK!
            threshold=40.0,
            levels=(5., 10.),
            value_store=value_store,
        ))
