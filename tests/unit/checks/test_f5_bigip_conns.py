#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.base.check_legacy_includes.f5_bigip import get_conn_rate_params

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
def test_get_conn_rate_params(
    config: Mapping[str, object],
    result: object,
) -> None:
    assert get_conn_rate_params(config) == result


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
def test_get_conn_rate_params_exception(config: Mapping[str, object], exception_msg: str) -> None:
    with pytest.raises(ValueError, match=exception_msg):
        get_conn_rate_params(config)
