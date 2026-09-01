#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import repeat
from typing import assert_never, Final

from cmk.graphing_engine import (
    EvaluatedBidirectional,
    EvaluatedFocusBound,
    EvaluatedPerfometer,
    EvaluatedPerfometerLayout,
    EvaluatedSegment,
    EvaluatedStacked,
    FocusBoundKind,
    Unit,
)
from cmk.gui.log import logger
from cmk.gui.utils.temperate_unit import TemperatureUnit

from ._engine_unit_format import unit_to_unit_format
from ._unit import user_specific_unit_from_unit_format
from ._utils import Linear


@dataclass(frozen=True, kw_only=True)
class DrawnSegment:
    share: float
    color: str | None


@dataclass(frozen=True, kw_only=True)
class _ArcTan:
    """
    Evaluates the following function:
    f(x) = (2 / π) * s * atan((π / 2) * (mᵢ / s) * (x - xᵢ)) + yᵢ
    (xᵢ|yᵢ) is the inflection point.
    mᵢ is the slope at the inflection point.
    s is the scale in units of π/2. The range of f is (yᵢ - s, yᵢ + s).
    """

    x_inflection: float
    y_inflection: float
    slope_inflection: float
    scale_in_units_of_pi_half: float

    def __call__(self, x: int | float) -> float:
        scale = self.scale_in_units_of_pi_half * 2 / math.pi
        return (
            scale * math.atan(self.slope_inflection / scale * (x - self.x_inflection))
            + self.y_inflection
        )


@dataclass(frozen=True, kw_only=True)
class _Projection:
    """
    Map arbitrarily large or small metric values to an interval (lower_limit, upper_limit), which
    indicates the fill level of a perfometer. lower_limit means that the perfometer is empty.
    upper_limit means that the perfometer is completely filled. The values of lower_limit and
    upper_limit depend on the type of the perfometer.

    The idea is to split the interval (lower_limit, upper_limit) into three parts:
    - A lower non-linear part, which has a lower limit of lower_limit.
    - A focus part in the middle (linear).
    - An upper non-linear part which has an upper limit of upper_limit.

    For the non-linear parts, there are currently two options:
    1) Hard cutoff ("Closed" in terms of graphing API)
      Values smaller than the lower end of the linear part are simply mapped to lower_limit.
      Values larger than the upper end of the linear part are simply mapped to upper_limit.
      In this case, the linear part starts/ends at lower_limit/upper_limit.

    2) Arcus tangent ("Open" in terms of graphing API)
      We splice the lower and/or upper end of the linear part with an arctan function. The splicing
      fulfills the following conditions:
      * At the splicing point, the values of the linear and the arctan function match (continuity).
      * At the splicing point, the slope of the linear and the arctan function match (continuously differentiable).
      * The splicing point is the inflection point of the arctan function. As a consequence, also the
        second derivatives match at the splicing point, since they both vanish. Note that there is
        no obvious reason for this choice, it is however a convenient point to use. Also, we need to
        make a choice (or two choices, one for the lower and one for the upper non-linear part) to
        nail down all four parameters of
        a * atan(b * x + c) + d.
      In this case, the linear part starts/ends above/below lower_limit/upper_limit.
    """

    start_of_focus_range: float
    end_of_focus_range: float
    lower_splice: _ArcTan | None
    focus_projection: Linear
    upper_splice: _ArcTan | None

    def __call__(self, value: int | float) -> float:
        if value < self.start_of_focus_range:
            if self.lower_splice is None:
                return self.focus_projection(self.start_of_focus_range)
            return self.lower_splice(value)
        if value > self.end_of_focus_range:
            if self.upper_splice is None:
                return self.focus_projection(self.end_of_focus_range)
            return self.upper_splice(value)
        return self.focus_projection(value)


_EMPTY_AT: Final = 0.0


@dataclass(frozen=True, kw_only=True)
class _ProjectionParameters:
    lower_open_end: float
    upper_open_start: float
    perfometer_full_at: float


_SINGLE_PARAMETERS = _ProjectionParameters(
    lower_open_end=15.0,
    upper_open_start=85.0,
    perfometer_full_at=100.0,
)

_OPPOSED_PARAMETERS = _ProjectionParameters(
    lower_open_end=5.0,
    upper_open_start=45.0,
    perfometer_full_at=50.0,
)

_ZERO = EvaluatedFocusBound(bound_kind=FocusBoundKind.CLOSED, value=0.0)


def _make_projection(
    lower: EvaluatedFocusBound,
    upper: EvaluatedFocusBound,
    parameters: _ProjectionParameters,
    perfometer_name: str,
) -> _Projection:
    if lower.value >= upper.value:
        logger.debug(
            "Cannot compute the range from %(lower_x)s and %(upper_x)s of the perfometer %(perfometer_name)s",
            {
                "lower_x": lower.value,
                "upper_x": upper.value,
                "perfometer_name": perfometer_name,
            },
        )
        return _Projection(
            start_of_focus_range=float("nan"),
            end_of_focus_range=float("nan"),
            lower_splice=None,
            focus_projection=Linear(slope=float("nan"), intercept=float("nan")),
            upper_splice=None,
        )

    lower_y = _EMPTY_AT if lower.bound_kind is FocusBoundKind.CLOSED else parameters.lower_open_end
    upper_y = (
        parameters.perfometer_full_at
        if upper.bound_kind is FocusBoundKind.CLOSED
        else parameters.upper_open_start
    )
    linear = Linear.fit_to_two_points(p_1=(lower.value, lower_y), p_2=(upper.value, upper_y))
    return _Projection(
        start_of_focus_range=lower.value,
        end_of_focus_range=upper.value,
        lower_splice=(
            None
            if lower.bound_kind is FocusBoundKind.CLOSED
            else _ArcTan(
                x_inflection=lower.value,
                y_inflection=parameters.lower_open_end,
                slope_inflection=linear.slope,
                scale_in_units_of_pi_half=parameters.lower_open_end - _EMPTY_AT,
            )
        ),
        focus_projection=linear,
        upper_splice=(
            None
            if upper.bound_kind is FocusBoundKind.CLOSED
            else _ArcTan(
                x_inflection=upper.value,
                y_inflection=parameters.upper_open_start,
                slope_inflection=linear.slope,
                scale_in_units_of_pi_half=parameters.perfometer_full_at
                - parameters.upper_open_start,
            )
        ),
    )


def _project_segments(
    projection: _Projection,
    segments: Sequence[EvaluatedSegment],
    fully_filled_at: float,
) -> list[DrawnSegment]:
    value_total = sum(segment.value for segment in segments)
    filled_total = projection(value_total)

    projected_values = [projection(segment.value) for segment in segments]
    projected_values_sum = sum(projected_values)
    segments_share_of_filled = (
        repeat(0.0, len(segments))
        if projected_values_sum == 0.0
        else [(p / projected_values_sum) for p in projected_values]
    )
    drawn = [
        DrawnSegment(share=round(filled_total * share, 2), color=segment.attributes.color)
        for segment, share in zip(segments, segments_share_of_filled, strict=True)
    ]
    drawn.append(
        DrawnSegment(share=round(fully_filled_at - sum(d.share for d in drawn), 2), color=None)
    )
    if not (drawn := [d for d in drawn if not math.isnan(d.share)]):
        return [DrawnSegment(share=0.0, color=None)]
    return drawn


def _drawn_bar(
    bar: EvaluatedPerfometer,
    parameters: _ProjectionParameters,
    lower: EvaluatedFocusBound | None = None,
) -> list[DrawnSegment]:
    return _project_segments(
        _make_projection(
            bar.focus_range.lower if lower is None else lower,
            bar.focus_range.upper,
            parameters,
            bar.name,
        ),
        bar.segments,
        parameters.perfometer_full_at,
    )


def drawn_segments(perfometer: EvaluatedPerfometerLayout) -> Sequence[Sequence[DrawnSegment]]:
    match perfometer:
        case EvaluatedPerfometer():
            return [_drawn_bar(perfometer, _SINGLE_PARAMETERS)]
        case EvaluatedBidirectional():
            left = _drawn_bar(perfometer.left, _OPPOSED_PARAMETERS, _ZERO)
            right = _drawn_bar(perfometer.right, _OPPOSED_PARAMETERS, _ZERO)
            return [[*left[::-1], *right]]
        case EvaluatedStacked():
            return [
                _drawn_bar(perfometer.upper, _SINGLE_PARAMETERS),
                _drawn_bar(perfometer.lower, _SINGLE_PARAMETERS),
            ]
        case _:
            assert_never(perfometer)


def _render_value(value: float, unit: Unit, temperature_unit: TemperatureUnit) -> str:
    specific = user_specific_unit_from_unit_format(unit_to_unit_format(unit), temperature_unit)
    return specific.formatter.render(specific.conversion(value))


def _bar_label(bar: EvaluatedPerfometer, temperature_unit: TemperatureUnit) -> str:
    return _render_value(
        sum(segment.value for segment in bar.segments),
        bar.segments[0].attributes.unit,
        temperature_unit,
    )


def perfometer_label(
    perfometer: EvaluatedPerfometerLayout, temperature_unit: TemperatureUnit
) -> str:
    match perfometer:
        case EvaluatedPerfometer():
            return _bar_label(perfometer, temperature_unit)
        case EvaluatedBidirectional():
            bars = (perfometer.left, perfometer.right)
        case EvaluatedStacked():
            bars = (perfometer.upper, perfometer.lower)
        case _:
            assert_never(perfometer)
    return " / ".join(label for bar in bars if (label := _bar_label(bar, temperature_unit)))


def perfometer_sort_value(perfometer: EvaluatedPerfometerLayout) -> float:
    match perfometer:
        case EvaluatedPerfometer():
            return sum(segment.value for segment in perfometer.segments)
        case EvaluatedBidirectional():
            return max(
                perfometer_sort_value(perfometer.left), perfometer_sort_value(perfometer.right)
            )
        case EvaluatedStacked():
            return perfometer_sort_value(perfometer.upper)
        case _:
            assert_never(perfometer)
