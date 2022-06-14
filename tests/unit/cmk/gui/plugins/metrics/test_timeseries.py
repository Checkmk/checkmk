#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.exceptions import MKGeneralException

import cmk.gui.plugins.metrics.timeseries as ts


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("%", []), id="Unknown symbol"),
    ],
)
def test_time_series_math_exc_symbol(args) -> None:
    with pytest.raises(MKGeneralException, match="Undefined operator"):
        ts.time_series_math(*args)


@pytest.mark.skip(reason="Skip operations when incorrect amount of timeseries data for operator")
@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("MAX", []), id="MAX requires at least a timeseries"),
        pytest.param(
            ("/", [ts.TimeSeries([0, 180, 60, 5, 5, 10])]), id="Division exclusive on pairs #1"
        ),
        pytest.param(
            ("/", [ts.TimeSeries([0, 180, 60, 5, 5, 10])] * 3), id="Division exclusive on pairs #2"
        ),
    ],
)
def test_time_series_math_exc(args) -> None:
    with pytest.raises(MKGeneralException):
        ts.time_series_math(*args)


@pytest.mark.parametrize("operator", ["+", "*", "MAX", "MIN", "AVERAGE", "MERGE"])
def test_time_series_math_stable_singles(operator) -> None:
    test_ts = ts.TimeSeries([0, 180, 60, 6, 5, 10, None, -2, -3.14])
    assert ts.time_series_math(operator, [test_ts]) == test_ts
