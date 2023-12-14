#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import perfometer


def test_closed_error_empty_bound() -> None:
    with pytest.raises(ValueError):
        perfometer.Closed("")


def test_open_error_empty_bound() -> None:
    with pytest.raises(ValueError):
        perfometer.Open("")


def test_perfometer_error_empty_name() -> None:
    focus_range = perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100))
    segments = ["metric-name"]
    with pytest.raises(ValueError):
        perfometer.Perfometer(name="", focus_range=focus_range, segments=segments)


def test_perfometer_error_missing_segments() -> None:
    name = "name"
    focus_range = perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100))
    with pytest.raises(AssertionError):
        perfometer.Perfometer(name=name, focus_range=focus_range, segments=[])


def test_perfometer_error_segments_empty_name() -> None:
    name = "name"
    focus_range = perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100))
    with pytest.raises(ValueError):
        perfometer.Perfometer(name=name, focus_range=focus_range, segments=[""])


def test_bidirectional_error_empty_name() -> None:
    left = perfometer.Perfometer(
        name="left",
        focus_range=perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100)),
        segments=["metric-name-1"],
    )
    right = perfometer.Perfometer(
        name="right",
        focus_range=perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100)),
        segments=["metric-name-2"],
    )
    with pytest.raises(ValueError):
        perfometer.Bidirectional(name="", left=left, right=right)


def test_stacked_error_empty_name() -> None:
    lower = perfometer.Perfometer(
        name="lower",
        focus_range=perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100)),
        segments=["metric-name-1"],
    )
    upper = perfometer.Perfometer(
        name="upper",
        focus_range=perfometer.FocusRange(perfometer.Closed(0), perfometer.Closed(100)),
        segments=["metric-name-2"],
    )
    with pytest.raises(ValueError):
        perfometer.Stacked(name="", lower=lower, upper=upper)
