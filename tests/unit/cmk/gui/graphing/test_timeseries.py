#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.prediction import TimeSeries

from cmk.gui.graphing._timeseries import _time_series_math
from cmk.gui.graphing._type_defs import Operators


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("%", []), id="Unknown symbol"),
    ],
)
def test__time_series_math_exc_symbol(args: tuple[Literal["%"], list[TimeSeries]]) -> None:
    with pytest.raises(MKGeneralException, match="Undefined operator"):
        _time_series_math(*args)  # type: ignore[arg-type]


@pytest.mark.skip(reason="Skip operations when incorrect amount of timeseries data for operator")
@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("MAX", []), id="MAX requires at least a timeseries"),
        pytest.param(
            ("/", [TimeSeries([0, 180, 60, 5, 5, 10])]), id="Division exclusive on pairs #1"
        ),
        pytest.param(
            ("/", [TimeSeries([0, 180, 60, 5, 5, 10])] * 3), id="Division exclusive on pairs #2"
        ),
    ],
)
def test__time_series_math_exc(args: tuple[Operators, list[TimeSeries]]) -> None:
    with pytest.raises(MKGeneralException):
        _time_series_math(*args)


@pytest.mark.parametrize("operator", ["+", "*", "MAX", "MIN", "AVERAGE", "MERGE"])
def test__time_series_math_stable_singles(operator: Operators) -> None:
    test_ts = TimeSeries([0, 180, 60, 6, 5, 10, None, -2, -3.14])
    assert _time_series_math(operator, [test_ts]) == test_ts
