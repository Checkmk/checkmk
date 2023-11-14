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
            "",
            [metric.MetricName("metric-name")],
            upper_bound=upper_bound,
            lower_bound=lower_bound,
        )


def test_perfometer_error_missing_segments() -> None:
    upper_bound = perfometer.Closed(100)
    lower_bound = perfometer.Closed(0)
    with pytest.raises(AssertionError):
        perfometer.Perfometer(
            "perfometer-name",
            [],
            upper_bound=upper_bound,
            lower_bound=lower_bound,
        )


def test_bidirectional_error_missing_name() -> None:
    left = perfometer.Perfometer(
        "perfometer-name-left",
        [metric.MetricName("metric-name")],
        upper_bound=perfometer.Closed(100),
        lower_bound=perfometer.Closed(0),
    )
    right = perfometer.Perfometer(
        "perfometer-name-right",
        [metric.MetricName("metric-name")],
        upper_bound=perfometer.Closed(100),
        lower_bound=perfometer.Closed(0),
    )
    with pytest.raises(AssertionError):
        perfometer.Bidirectional("", left=left, right=right)


def test_stacked_error_missing_name() -> None:
    upper = perfometer.Perfometer(
        "perfometer-name-left",
        [metric.MetricName("metric-name")],
        upper_bound=perfometer.Closed(100),
        lower_bound=perfometer.Closed(0),
    )
    lower = perfometer.Perfometer(
        "perfometer-name-right",
        [metric.MetricName("metric-name")],
        upper_bound=perfometer.Closed(100),
        lower_bound=perfometer.Closed(0),
    )
    with pytest.raises(AssertionError):
        perfometer.Stacked("", upper=upper, lower=lower)
