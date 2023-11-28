#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import metric, perfometer


def test_perfometer_error_empty_name() -> None:
    focus_range = perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100))
    segments = [metric.Name("metric-name")]
    with pytest.raises(ValueError):
        perfometer.Perfometer("", focus_range, segments)


def test_perfometer_error_missing_segments() -> None:
    name = "name"
    focus_range = perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100))
    with pytest.raises(AssertionError):
        perfometer.Perfometer(name, focus_range, [])


def test_bidirectional_error_empty_name() -> None:
    left = perfometer.Perfometer(
        "left",
        perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100)),
        [metric.Name("metric-name-1")],
    )
    right = perfometer.Perfometer(
        "right",
        perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100)),
        [metric.Name("metric-name-2")],
    )
    with pytest.raises(ValueError):
        perfometer.Bidirectional("", left=left, right=right)


def test_stacked_error_empty_name() -> None:
    lower = perfometer.Perfometer(
        "lower",
        perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100)),
        [metric.Name("metric-name-1")],
    )
    upper = perfometer.Perfometer(
        "upper",
        perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100)),
        [metric.Name("metric-name-2")],
    )
    with pytest.raises(ValueError):
        perfometer.Stacked("", lower=lower, upper=upper)
