#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import metric, perfometer


def test_perfometer_error_missing_name() -> None:
    upper_bound = perfometer.Closed(100)
    lower_bound = perfometer.Closed(0)
    with pytest.raises(AssertionError):
        perfometer.Perfometer(
            name="",
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            segments=[metric.MetricName("metric-name")],
        )


def test_perfometer_error_missing_segments() -> None:
    upper_bound = perfometer.Closed(100)
    lower_bound = perfometer.Closed(0)
    with pytest.raises(AssertionError):
        perfometer.Perfometer(
            name="perfometer-name",
            upper_bound=upper_bound,
            lower_bound=lower_bound,
            segments=[],
        )


def test_bidirectional_error_missing_name() -> None:
    left = perfometer.Perfometer(
        name="perfometer-name-left",
        upper_bound=perfometer.Closed(100),
        lower_bound=perfometer.Closed(0),
        segments=[metric.MetricName("metric-name")],
    )
    right = perfometer.Perfometer(
        name="perfometer-name-right",
        upper_bound=perfometer.Closed(100),
        lower_bound=perfometer.Closed(0),
        segments=[metric.MetricName("metric-name")],
    )
    with pytest.raises(AssertionError):
        perfometer.Bidirectional(name="", left=left, right=right)


def test_stacked_error_missing_name() -> None:
    upper = perfometer.Perfometer(
        name="perfometer-name-left",
        upper_bound=perfometer.Closed(100),
        lower_bound=perfometer.Closed(0),
        segments=[metric.MetricName("metric-name")],
    )
    lower = perfometer.Perfometer(
        name="perfometer-name-right",
        upper_bound=perfometer.Closed(100),
        lower_bound=perfometer.Closed(0),
        segments=[metric.MetricName("metric-name")],
    )
    with pytest.raises(AssertionError):
        perfometer.Stacked(name="", upper=upper, lower=lower)
