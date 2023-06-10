#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from collections.abc import Callable
from unittest.mock import Mock

import pytest

from cmk.checkengine.submitters import ServiceDetails, ServiceState

import cmk.base.config as config
from cmk.base import check_api


@pytest.mark.parametrize("value_eight", ["8", 8])
def test_oid_spec_binary(value_eight: str | int) -> None:
    oid_bin = check_api.BINARY(value_eight)
    assert oid_bin.column == "8"
    assert oid_bin.encoding == "binary"
    assert oid_bin.save_to_cache is False


@pytest.mark.parametrize("value_eight", ["8", 8])
def test_oid_spec_cached(value_eight: str | int) -> None:
    oid_cached = check_api.CACHED_OID(value_eight)
    assert oid_cached.column == "8"
    assert oid_cached.encoding == "string"
    assert oid_cached.save_to_cache is True


@pytest.mark.parametrize(
    "value, levels, representation, unit, result",
    [
        (5, (3, 6), int, "", (1, " (warn/crit at 3/6)")),
        (7, (3, 6), lambda x: "%.1f m" % x, "", (2, " (warn/crit at 3.0 m/6.0 m)")),
        (7, (3, 6), lambda x: "%.1f" % x, " m", (2, " (warn/crit at 3.0 m/6.0 m)")),
        (2, (3, 6, 1, 0), int, "", (0, "")),
        (1, (3, 6, 1, 0), int, "", (0, "")),
        (0, (3, 6, 1, 0), int, "", (1, " (warn/crit below 1/0)")),
        (-1, (3, 6, 1, 0), int, "", (2, " (warn/crit below 1/0)")),
    ],
)
def test_boundaries(
    value: float,
    levels: check_api.Levels,
    representation: Callable,
    unit: str,
    result: tuple[ServiceState, ServiceDetails],
) -> None:
    assert check_api._do_check_levels(value, levels, representation, unit) == result


@pytest.mark.parametrize(
    "value, dsname, params, kwargs, result",
    [
        (
            5,
            "battery",
            None,
            {"human_readable_func": check_api.get_percent_human_readable},
            (0, "5.00%", [("battery", 5, None, None)]),
        ),
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
    dsname: check_api.MetricName | None,
    params: None | tuple[float, ...],
    kwargs,
    result: check_api.ServiceCheckResult,
) -> None:
    assert check_api.check_levels(value, dsname, params, **kwargs) == result


def test_http_proxy(mocker: Mock) -> None:
    proxy_patch = mocker.patch.object(config, "get_http_proxy")
    check_api.get_http_proxy(("url", "http://xy:123"))
    assert proxy_patch.called_once()
