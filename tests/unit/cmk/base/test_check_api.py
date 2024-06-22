#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import math
from collections.abc import Callable
from unittest.mock import Mock

import pytest

from cmk.utils.metrics import MetricName

from cmk.checkengine.submitters import ServiceDetails, ServiceState

from cmk.base import check_api


@pytest.mark.parametrize(
    "value, levels, representation, result",
    [
        (5, (3, 6), int, (1, " (warn/crit at 3/6)")),
        (7, (3, 6), lambda x: "%.1f m" % x, (2, " (warn/crit at 3.0 m/6.0 m)")),
        (2, (3, 6, 1, 0), int, (0, "")),
        (1, (3, 6, 1, 0), int, (0, "")),
        (0, (3, 6, 1, 0), int, (1, " (warn/crit below 1/0)")),
        (-1, (3, 6, 1, 0), int, (2, " (warn/crit below 1/0)")),
    ],
)
def test_boundaries(
    value: float,
    levels: check_api.Levels,
    representation: Callable,
    result: tuple[ServiceState, ServiceDetails],
) -> None:
    assert check_api._do_check_levels(value, levels, representation) == result


@pytest.mark.parametrize(
    "value, dsname, params, kwargs, result",
    [
        (
            6,
            "disk",
            (4, 8),
            {"unit": "years", "infoname": "Disk Age"},
            (1, "Disk Age: 6.00 years (warn/crit at 4.00 years/8.00 years)", [("disk", 6.0, 4, 8)]),
        ),
        (
            5e-7,
            "H_concentration",
            (4e-7, 8e-7, 5e-8, 2e-8),
            {
                "human_readable_func": lambda x: "pH %.1f" % -math.log10(x),
                "infoname": "Water acidity",
            },
            (
                1,
                "Water acidity: pH 6.3 (warn/crit at pH 6.4/pH 6.1)",
                [("H_concentration", 5e-7, 4e-7, 8e-7)],
            ),
        ),
        (
            5e-7,
            "H_concentration",
            (4e-7, 8e-7, 5e-8, 2e-8),
            {
                "human_readable_func": lambda x: "pH %.1f" % -math.log10(x),
                "unit": "??",
                "infoname": "Water acidity",
            },
            (
                1,
                "Water acidity: pH 6.3 ?? (warn/crit at pH 6.4 ??/pH 6.1 ??)",
                [("H_concentration", 5e-7, 4e-7, 8e-7)],
            ),
        ),
    ],
)
def test_check_levels(  # type: ignore[no-untyped-def]
    value: float,
    dsname: MetricName | None,
    params: None | tuple[float, ...],
    kwargs,
    result: check_api.ServiceCheckResult,
) -> None:
    assert check_api.check_levels(value, dsname, params, **kwargs) == result


def test_http_proxy(mocker: Mock) -> None:
    proxy_patch = mocker.patch.object(check_api, "_get_http_proxy")
    check_api.get_http_proxy(("url", "http://xy:123"))
    proxy_patch.assert_called_once()
