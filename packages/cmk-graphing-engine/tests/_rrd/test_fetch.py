#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing_engine import time_series_of_rrd_column, TimeRange, TimeSeries


def test_a_column_reads_its_grid_from_the_header() -> None:
    assert time_series_of_rrd_column([0.0, 120.0, 60.0, 1.0, None]) == TimeSeries(
        time_range=TimeRange(start=0, end=120, step=60), values=[1.0, None]
    )


def test_a_column_without_values_holds_no_series() -> None:
    assert time_series_of_rrd_column([0.0, 120.0, 60.0]) is None


def test_a_column_with_a_gap_in_its_header_is_refused() -> None:
    with pytest.raises(ValueError):
        time_series_of_rrd_column([0.0, None, 60.0, 1.0])
