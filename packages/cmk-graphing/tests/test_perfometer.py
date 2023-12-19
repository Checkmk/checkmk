#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import perfometers


def test_closed_error_empty_bound() -> None:
    with pytest.raises(ValueError):
        perfometers.Closed("")


def test_open_error_empty_bound() -> None:
    with pytest.raises(ValueError):
        perfometers.Open("")


def test_perfometer_error_empty_name() -> None:
    focus_range = perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100))
    segments = ["metric-name"]
    with pytest.raises(ValueError):
        perfometers.Perfometer(name="", focus_range=focus_range, segments=segments)


def test_perfometer_error_missing_segments() -> None:
    name = "name"
    focus_range = perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100))
    with pytest.raises(AssertionError):
        perfometers.Perfometer(name=name, focus_range=focus_range, segments=[])


def test_perfometer_error_segments_empty_name() -> None:
    name = "name"
    focus_range = perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100))
    with pytest.raises(ValueError):
        perfometers.Perfometer(name=name, focus_range=focus_range, segments=[""])


def test_bidirectional_error_empty_name() -> None:
    left = perfometers.Perfometer(
        name="left",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
        segments=["metric-name-1"],
    )
    right = perfometers.Perfometer(
        name="right",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
        segments=["metric-name-2"],
    )
    with pytest.raises(ValueError):
        perfometers.Bidirectional(name="", left=left, right=right)


def test_stacked_error_empty_name() -> None:
    lower = perfometers.Perfometer(
        name="lower",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
        segments=["metric-name-1"],
    )
    upper = perfometers.Perfometer(
        name="upper",
        focus_range=perfometers.FocusRange(perfometers.Closed(0), perfometers.Closed(100)),
        segments=["metric-name-2"],
    )
    with pytest.raises(ValueError):
        perfometers.Stacked(name="", lower=lower, upper=upper)
