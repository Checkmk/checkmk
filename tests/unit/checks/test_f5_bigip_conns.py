#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "config, result",
    [
        ({}, (None, None, None, None)),
        (
            {
                "connections_rate": (2, 5),
                "connections_rate_lower": (1, 0),
            },
            (2, 5, 1, 0),
        ),
        (
            {
                "connections_rate_lower": (1, 0),
            },
            (None, None, 1, 0),
        ),
        (
            {
                "connections_rate": (2, 5),
            },
            (2, 5, None, None),
        ),
        (
            {
                "connections_rate": {
                    "levels_upper": ("absolute", (0.0, 0.0)),
                    "levels_lower": ("stdev", (2.0, 4.0)),
                    "period": "wday",
                    "horizon": 90,
                },
            },
            {
                "levels_upper": ("absolute", (0.0, 0.0)),
                "levels_lower": ("stdev", (2.0, 4.0)),
                "period": "wday",
                "horizon": 90,
            },
        ),
    ],
)
def test_get_conn_rate_params(config, result):
    check = Check("f5_bigip_conns")
    assert check.context["get_conn_rate_params"](config) == result


@pytest.mark.parametrize(
    "config, exception_msg",
    [
        (
            {
                "connections_rate": {
                    "levels_upper": ("absolute", (0.0, 0.0)),
                    "levels_lower": ("stdev", (2.0, 4.0)),
                    "period": "wday",
                    "horizon": 90,
                },
                "connections_rate_lower": (1, 0),
            },
            (
                "Can't configure minimum connections per second when the maximum "
                "connections per second is setup in predictive levels. Please use the given "
                "lower bound specified in the maximum connections, or set maximum "
                "connections to use fixed levels."
            ),
        )
    ],
)
def test_get_conn_rate_params_exception(config, exception_msg):
    check = Check("f5_bigip_conns")
    with pytest.raises(ValueError, match=exception_msg):
        check.context["get_conn_rate_params"](config)
