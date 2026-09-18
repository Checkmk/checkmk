#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from cmk.agent_based.prediction_backend import PredictionInfo, PredictionParameters
from cmk.utils.prediction import DataStat, estimate_levels


def _meta(
    direction: Literal["upper", "lower"],
    levels: tuple[Literal["absolute", "relative", "stdev"], tuple[float, float]],
    bound: tuple[float, float] | None,
) -> PredictionInfo:
    return PredictionInfo(
        valid_interval=(0, 86400),
        metric="rocket_fuel",
        direction=direction,
        params=PredictionParameters(period="wday", horizon=90, levels=levels, bound=bound),
    )


def _reference(average: float, stdev: float | None) -> DataStat:
    return DataStat(average=average, min_=average, max_=average, stdev=stdev)


def test_estimate_levels_absolute() -> None:
    assert estimate_levels(_meta("upper", ("absolute", (2, 4)), None), _reference(0, 2)) == (2, 4)


def test_estimate_levels_zero_reference_relative() -> None:
    assert estimate_levels(_meta("upper", ("relative", (2, 4)), None), _reference(0, 2)) is None


def test_estimate_levels_stdev() -> None:
    assert estimate_levels(_meta("upper", ("stdev", (2, 4)), None), _reference(0, 2)) == (4, 8)


def test_estimate_levels_stdev_lower() -> None:
    assert estimate_levels(_meta("lower", ("stdev", (3, 5)), None), _reference(15, 2)) == (9, 5)


def test_estimate_levels_upper_unbounded() -> None:
    assert estimate_levels(_meta("upper", ("stdev", (2.3, 3.2)), None), _reference(42.0, 1.0)) == (
        44.3,
        45.2,
    )


def test_estimate_levels_upper_lbound() -> None:
    assert estimate_levels(
        _meta("upper", ("stdev", (2.3, 3.2)), (45.0, 45.0)), _reference(42.0, 1.0)
    ) == (45.0, 45.2)


def test_estimate_levels_lower_unbounded() -> None:
    assert estimate_levels(_meta("lower", ("stdev", (2.3, 3.2)), None), _reference(42.0, 1.0)) == (
        39.7,
        38.8,
    )


def test_estimate_levels_lower_ubound() -> None:
    assert estimate_levels(
        _meta("lower", ("stdev", (2.3, 3.2)), (38.5, 50.0)), _reference(42.0, 1.0)
    ) == (38.5, 38.8)
