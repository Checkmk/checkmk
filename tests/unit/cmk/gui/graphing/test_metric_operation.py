#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.graphing._metric_operation import _time_series_math, Operators
from cmk.gui.graphing._time_series import TimeSeries


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("%", []), id="Unknown symbol"),
    ],
)
def test__time_series_math_exc_symbol(args: tuple[Literal["%"], list[TimeSeries]]) -> None:
    with pytest.raises(MKGeneralException, match="Undefined operator"):
        _time_series_math(*args)  # type: ignore[arg-type]


@pytest.mark.parametrize("operator", ["+", "*", "MAX", "MIN", "AVERAGE", "MERGE"])
def test__time_series_math_stable_singles(operator: Operators) -> None:
    test_ts = TimeSeries([0, 180, 60, 6, 5, 10, None, -2, -3.14])
    assert _time_series_math(operator, [test_ts]) == test_ts
