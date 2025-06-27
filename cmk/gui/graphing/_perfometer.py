#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import repeat
from typing import assert_never, Self

from cmk.gui.config import active_config
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.view_utils import get_themed_perfometer_bg_color

from cmk.graphing.v1 import metrics as metrics_api
from cmk.graphing.v1 import perfometers as perfometers_api

from ._color import parse_color_from_api
from ._from_api import parse_unit_from_api
from ._translated_metrics import TranslatedMetric
from ._unit import ConvertibleUnitSpecification, user_specific_unit

type Quantity = (
    str
    | metrics_api.Constant
    | metrics_api.WarningOf
    | metrics_api.CriticalOf
    | metrics_api.MinimumOf
    | metrics_api.MaximumOf
    | metrics_api.Sum
    | metrics_api.Product
    | metrics_api.Difference
    | metrics_api.Fraction
)


@dataclass(frozen=True)
class _MetricNamesOrScalars:
    _metric_names: list[str]
    _scalars: list[
        metrics_api.WarningOf
        | metrics_api.CriticalOf
        | metrics_api.MinimumOf
        | metrics_api.MaximumOf
    ]

    def collect_quantity_names(self, quantity: Quantity) -> None:
        match quantity:
            case str():
                self._metric_names.append(quantity)
            case metrics_api.WarningOf():
                self._metric_names.append(quantity.metric_name)
                self._scalars.append(quantity)
            case metrics_api.CriticalOf():
                self._metric_names.append(quantity.metric_name)
                self._scalars.append(quantity)
            case metrics_api.MinimumOf():
                self._metric_names.append(quantity.metric_name)
                self._scalars.append(quantity)
            case metrics_api.MaximumOf():
                self._metric_names.append(quantity.metric_name)
                self._scalars.append(quantity)
            case metrics_api.Sum():
                for s in quantity.summands:
                    self.collect_quantity_names(s)
            case metrics_api.Product():
                for f in quantity.factors:
                    self.collect_quantity_names(f)
            case metrics_api.Difference():
                self.collect_quantity_names(quantity.minuend)
                self.collect_quantity_names(quantity.subtrahend)
            case metrics_api.Fraction():
                self.collect_quantity_names(quantity.dividend)
                self.collect_quantity_names(quantity.divisor)

    @classmethod
    def from_perfometers(cls, *perfometers_: perfometers_api.Perfometer) -> Self:
        instance = cls([], [])
        for perfometer in perfometers_:
            if not isinstance(perfometer.focus_range.lower.value, int | float):
                instance.collect_quantity_names(perfometer.focus_range.lower.value)
            if not isinstance(perfometer.focus_range.upper.value, int | float):
                instance.collect_quantity_names(perfometer.focus_range.upper.value)
            for s in perfometer.segments:
                instance.collect_quantity_names(s)
        return instance

    @property
    def metric_names(self) -> Sequence[str]:
        return self._metric_names

    @property
    def scalars(
        self,
    ) -> Sequence[
        metrics_api.WarningOf
        | metrics_api.CriticalOf
        | metrics_api.MinimumOf
        | metrics_api.MaximumOf
    ]:
        return self._scalars


def _perfometer_matches(
    perfometer: (
        perfometers_api.Perfometer | perfometers_api.Bidirectional | perfometers_api.Stacked
    ),
    translated_metrics: Mapping[str, TranslatedMetric],
) -> bool:
    assert translated_metrics

    match perfometer:
        case perfometers_api.Perfometer():
            metric_names_or_scalars = _MetricNamesOrScalars.from_perfometers(perfometer)
        case perfometers_api.Bidirectional():
            metric_names_or_scalars = _MetricNamesOrScalars.from_perfometers(
                perfometer.left,
                perfometer.right,
            )
        case perfometers_api.Stacked():
            metric_names_or_scalars = _MetricNamesOrScalars.from_perfometers(
                perfometer.lower,
                perfometer.upper,
            )

    if not metric_names_or_scalars.metric_names:
        return False

    for metric_name in metric_names_or_scalars.metric_names:
        if metric_name not in translated_metrics:
            return False

    for scalar in metric_names_or_scalars.scalars:
        if scalar.metric_name not in translated_metrics:
            return False

        match scalar:
            case metrics_api.WarningOf():
                scalar_name = "warn"
            case metrics_api.CriticalOf():
                scalar_name = "crit"
            case metrics_api.MinimumOf():
                scalar_name = "min"
            case metrics_api.MaximumOf():
                scalar_name = "max"

        if scalar_name not in translated_metrics[scalar.metric_name].scalar:
            return False

    return True


@dataclass(frozen=True)
class _EvaluatedQuantity:
    unit_spec: ConvertibleUnitSpecification
    color: str
    value: int | float


def _evaluate_quantity(
    quantity: Quantity, translated_metrics: Mapping[str, TranslatedMetric]
) -> _EvaluatedQuantity:
    match quantity:
        case str():
            translated_metric = translated_metrics[quantity]
            return _EvaluatedQuantity(
                translated_metric.unit_spec,
                translated_metric.color,
                translated_metrics[quantity].value,
            )
        case metrics_api.Constant():
            return _EvaluatedQuantity(
                parse_unit_from_api(quantity.unit),
                parse_color_from_api(quantity.color),
                quantity.value,
            )
        case metrics_api.WarningOf():
            translated_metric = translated_metrics[quantity.metric_name]
            return _EvaluatedQuantity(
                translated_metric.unit_spec,
                "#ffff00",
                translated_metric.scalar["warn"],
            )
        case metrics_api.CriticalOf():
            translated_metric = translated_metrics[quantity.metric_name]
            return _EvaluatedQuantity(
                translated_metric.unit_spec,
                "#ff0000",
                translated_metric.scalar["crit"],
            )
        case metrics_api.MinimumOf():
            translated_metric = translated_metrics[quantity.metric_name]
            return _EvaluatedQuantity(
                translated_metric.unit_spec,
                parse_color_from_api(quantity.color),
                translated_metric.scalar["min"],
            )
        case metrics_api.MaximumOf():
            translated_metric = translated_metrics[quantity.metric_name]
            return _EvaluatedQuantity(
                translated_metric.unit_spec,
                parse_color_from_api(quantity.color),
                translated_metric.scalar["max"],
            )
        case metrics_api.Sum():
            evaluated_first_summand = _evaluate_quantity(quantity.summands[0], translated_metrics)
            return _EvaluatedQuantity(
                evaluated_first_summand.unit_spec,
                parse_color_from_api(quantity.color),
                (
                    evaluated_first_summand.value
                    + sum(
                        _evaluate_quantity(s, translated_metrics).value
                        for s in quantity.summands[1:]
                    )
                ),
            )
        case metrics_api.Product():
            product = 1.0
            for f in quantity.factors:
                product *= _evaluate_quantity(f, translated_metrics).value
            return _EvaluatedQuantity(
                parse_unit_from_api(quantity.unit),
                parse_color_from_api(quantity.color),
                product,
            )
        case metrics_api.Difference():
            evaluated_minuend = _evaluate_quantity(quantity.minuend, translated_metrics)
            evaluated_subtrahend = _evaluate_quantity(quantity.subtrahend, translated_metrics)
            return _EvaluatedQuantity(
                evaluated_minuend.unit_spec,
                parse_color_from_api(quantity.color),
                evaluated_minuend.value - evaluated_subtrahend.value,
            )
        case metrics_api.Fraction():
            return _EvaluatedQuantity(
                parse_unit_from_api(quantity.unit),
                parse_color_from_api(quantity.color),
                (
                    _evaluate_quantity(quantity.dividend, translated_metrics).value
                    / _evaluate_quantity(quantity.divisor, translated_metrics).value
                ),
            )


MetricRendererStack = Sequence[Sequence[tuple[int | float, str]]]


@dataclass(frozen=True, kw_only=True)
class _Linear:
    slope: float
    intercept: float

    @classmethod
    def fit_to_two_points(
        cls,
        *,
        p_1: tuple[float, float],
        p_2: tuple[float, float],
    ) -> Self:
        slope = (p_2[1] - p_1[1]) / (p_2[0] - p_1[0])
        return cls(
            slope=slope,
            intercept=p_1[1] - slope * p_1[0],
        )

    def __call__(self, value: int | float) -> float:
        return self.slope * value + self.intercept


class _Cutoff: ...


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
class _ProjectionFromMetricValueToPerfFillLevel:
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
    lower_end_projection: _Cutoff | _ArcTan
    focus_projection: _Linear
    upper_end_projection: _Cutoff | _ArcTan

    def __call__(self, value: int | float) -> float:
        if value < self.start_of_focus_range:
            return self._project_to_upper_or_lower_end(
                value,
                self.lower_end_projection,
                self.start_of_focus_range,
            )
        if value > self.end_of_focus_range:
            return self._project_to_upper_or_lower_end(
                value,
                self.upper_end_projection,
                self.end_of_focus_range,
            )
        return self.focus_projection(value)

    @staticmethod
    def _project_to_upper_or_lower_end(
        value: float | int,
        projection: _Cutoff | _ArcTan,
        cutoff_value: float,
    ) -> float:
        match projection:
            case _Cutoff():
                return cutoff_value
            case _ArcTan():
                return projection(value)
            case _:
                assert_never(projection)


@dataclass(frozen=True, kw_only=True)
class _ProjectionParameters:
    perfometer_empty_at: float
    lower_open_end: float
    upper_open_start: float
    perfometer_full_at: float


def _make_projection(
    focus_range: perfometers_api.FocusRange,
    projection_parameters: _ProjectionParameters,
    translated_metrics: Mapping[str, TranslatedMetric],
    perfometer_name: str,
) -> _ProjectionFromMetricValueToPerfFillLevel:
    # TODO At the moment we have a unit conversion only for temperature metrics and we want to have
    # the orig value at the same place as the converted value, eg.:
    #              20 °C
    # |-------------|---------------------------------------------|
    #              68 °F
    # Generalize the following...
    conversion = (
        user_specific_unit(
            list(translated_metrics.values())[0].unit_spec, user, active_config
        ).conversion
        if len(translated_metrics) == 1
        else lambda v: v
    )

    if isinstance(focus_range.lower.value, int | float):
        lower_x = conversion(float(focus_range.lower.value))
    else:
        lower_x = _evaluate_quantity(focus_range.lower.value, translated_metrics).value

    if isinstance(focus_range.upper.value, int | float):
        upper_x = conversion(float(focus_range.upper.value))
    else:
        upper_x = _evaluate_quantity(focus_range.upper.value, translated_metrics).value

    if lower_x >= upper_x:
        logger.debug(
            "Cannot compute the range from %s and %s of the perfometer %s",
            lower_x,
            upper_x,
            perfometer_name,
        )
        return _ProjectionFromMetricValueToPerfFillLevel(
            start_of_focus_range=float("nan"),
            end_of_focus_range=float("nan"),
            lower_end_projection=_Cutoff(),
            focus_projection=_Linear(slope=float("nan"), intercept=float("nan")),
            upper_end_projection=_Cutoff(),
        )

    # Note: if we have closed boundaries and a value exceeds the lower or upper limit then we use
    # the related limit. With this the value is always visible, we don't have any execption and the
    # perfometer is not filled resp. completely filled.
    match focus_range.lower, focus_range.upper:
        case perfometers_api.Closed(), perfometers_api.Closed():
            return _ProjectionFromMetricValueToPerfFillLevel(
                start_of_focus_range=lower_x,
                end_of_focus_range=upper_x,
                lower_end_projection=_Cutoff(),
                focus_projection=_Linear.fit_to_two_points(
                    p_1=(lower_x, projection_parameters.perfometer_empty_at),
                    p_2=(upper_x, projection_parameters.perfometer_full_at),
                ),
                upper_end_projection=_Cutoff(),
            )

        case perfometers_api.Open(), perfometers_api.Closed():
            linear = _Linear.fit_to_two_points(
                p_1=(lower_x, projection_parameters.lower_open_end),
                p_2=(upper_x, projection_parameters.perfometer_full_at),
            )
            return _ProjectionFromMetricValueToPerfFillLevel(
                start_of_focus_range=lower_x,
                end_of_focus_range=upper_x,
                lower_end_projection=_ArcTan(
                    x_inflection=lower_x,
                    y_inflection=projection_parameters.lower_open_end,
                    slope_inflection=linear.slope,
                    scale_in_units_of_pi_half=projection_parameters.lower_open_end
                    - projection_parameters.perfometer_empty_at,
                ),
                focus_projection=linear,
                upper_end_projection=_Cutoff(),
            )

        case perfometers_api.Closed(), perfometers_api.Open():
            linear = _Linear.fit_to_two_points(
                p_1=(lower_x, projection_parameters.perfometer_empty_at),
                p_2=(upper_x, projection_parameters.upper_open_start),
            )
            return _ProjectionFromMetricValueToPerfFillLevel(
                start_of_focus_range=lower_x,
                end_of_focus_range=upper_x,
                lower_end_projection=_Cutoff(),
                focus_projection=linear,
                upper_end_projection=_ArcTan(
                    x_inflection=upper_x,
                    y_inflection=projection_parameters.upper_open_start,
                    slope_inflection=linear.slope,
                    scale_in_units_of_pi_half=projection_parameters.perfometer_full_at
                    - projection_parameters.upper_open_start,
                ),
            )

        case perfometers_api.Open(), perfometers_api.Open():
            linear = _Linear.fit_to_two_points(
                p_1=(lower_x, projection_parameters.lower_open_end),
                p_2=(upper_x, projection_parameters.upper_open_start),
            )
            return _ProjectionFromMetricValueToPerfFillLevel(
                start_of_focus_range=lower_x,
                end_of_focus_range=upper_x,
                lower_end_projection=_ArcTan(
                    x_inflection=lower_x,
                    y_inflection=projection_parameters.lower_open_end,
                    slope_inflection=linear.slope,
                    scale_in_units_of_pi_half=projection_parameters.lower_open_end
                    - projection_parameters.perfometer_empty_at,
                ),
                focus_projection=linear,
                upper_end_projection=_ArcTan(
                    x_inflection=upper_x,
                    y_inflection=projection_parameters.upper_open_start,
                    slope_inflection=linear.slope,
                    scale_in_units_of_pi_half=projection_parameters.perfometer_full_at
                    - projection_parameters.upper_open_start,
                ),
            )

    assert False, focus_range


def _evaluate_segments(
    segments: Iterable[Quantity], translated_metrics: Mapping[str, TranslatedMetric]
) -> Sequence[_EvaluatedQuantity]:
    return [_evaluate_quantity(segment, translated_metrics) for segment in segments]


def _project_segments(
    projection: _ProjectionFromMetricValueToPerfFillLevel,
    segments: Sequence[_EvaluatedQuantity],
    fully_filled_at: float,
    themed_perfometer_bg_color: str,
) -> list[tuple[float, str]]:
    """Compute which portion of the perfometer needs to be filled with which color.

    The sum of the segments determines the total portion of the perfometer that is filled.
    This really only makes sense if the represent positve values, but we try to compute this
    in a way that at least does not crash in the general case.
    """
    value_total = sum(s.value for s in segments)
    filled_total = projection(value_total)  # ∈ [0.0, 100.0]

    projected_values = [projection(s.value) for s in segments]  # ∈ [0.0, 100.0]
    projected_values_sum = sum(projected_values)  # >= 0.0
    segments_share_of_filled = (
        repeat(0.0, len(segments))
        if projected_values_sum == 0.0
        else [(p / projected_values_sum) for p in projected_values]
    )
    projections = [
        (
            round(filled_total * share, 2),
            entry.color,
        )
        for entry, share in zip(segments, segments_share_of_filled, strict=True)
    ]
    projections.append(
        (
            round(fully_filled_at - sum(p[0] for p in projections), 2),
            themed_perfometer_bg_color,
        )
    )
    if not (projections := [p for p in projections if not math.isnan(p[0])]):
        return [(0.0, themed_perfometer_bg_color)]
    return projections


class MetricometerRenderer(abc.ABC):
    """Abstract base class for all metricometer renderers"""

    @classmethod
    def type_name(cls) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def get_stack(self) -> MetricRendererStack:
        """Return a list of perfometer elements

        Each element is represented by a 2 element tuple where the first element is
        the width in px and the second element the hex color code of this element.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_label(self) -> str:
        """Returns the label to be shown on top of the rendered stack

        When the perfometer type definition has a "label" element, this will be used.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_sort_value(self) -> float:
        """Returns the number to sort this perfometer with compared to the other
        performeters in the current performeter sort group"""
        raise NotImplementedError()

    @staticmethod
    def _render_value(unit_spec: ConvertibleUnitSpecification, value: float) -> str:
        return user_specific_unit(unit_spec, user, active_config).formatter.render(value)


class MetricometerRendererPerfometer(MetricometerRenderer):
    _PROJECTION_PARAMETERS = _ProjectionParameters(
        perfometer_empty_at=0.0,
        lower_open_end=15.0,
        upper_open_start=85.0,
        perfometer_full_at=100.0,
    )

    def __init__(
        self,
        perfometer: perfometers_api.Perfometer,
        translated_metrics: Mapping[str, TranslatedMetric],
        themed_perfometer_bg_color: str,
    ) -> None:
        # Needed for sorting via cmk/gui/views/perfometers/base.py::sort_value::_get_metrics_sort_group
        self.perfometer = perfometer
        self.translated_metrics = translated_metrics
        self.themed_perfometer_bg_color = themed_perfometer_bg_color

    @classmethod
    def type_name(cls) -> str:
        return "perfometer"

    def get_stack(self) -> MetricRendererStack:
        if projections := _project_segments(
            _make_projection(
                self.perfometer.focus_range,
                self._PROJECTION_PARAMETERS,
                self.translated_metrics,
                self.perfometer.name,
            ),
            _evaluate_segments(
                self.perfometer.segments,
                self.translated_metrics,
            ),
            self._PROJECTION_PARAMETERS.perfometer_full_at,
            self.themed_perfometer_bg_color,
        ):
            return [projections]
        return []

    def get_label(self) -> str:
        first_segment = _evaluate_quantity(self.perfometer.segments[0], self.translated_metrics)
        return user_specific_unit(
            first_segment.unit_spec,
            user,
            active_config,
        ).formatter.render(
            first_segment.value
            + sum(
                _evaluate_quantity(s, self.translated_metrics).value
                for s in self.perfometer.segments[1:]
            )
        )

    def get_sort_value(self) -> float:
        return sum(
            _evaluate_quantity(s, self.translated_metrics).value for s in self.perfometer.segments
        )


class MetricometerRendererBidirectional(MetricometerRenderer):
    _PROJECTION_PARAMETERS = _ProjectionParameters(
        perfometer_empty_at=0.0,
        lower_open_end=5.0,
        upper_open_start=45.0,
        perfometer_full_at=50.0,
    )

    def __init__(
        self,
        perfometer: perfometers_api.Bidirectional,
        translated_metrics: Mapping[str, TranslatedMetric],
        themed_perfometer_bg_color: str,
    ) -> None:
        # Needed for sorting via cmk/gui/views/perfometers/base.py::sort_value::_get_metrics_sort_group
        self.perfometer = perfometer
        self.translated_metrics = translated_metrics
        self.themed_perfometer_bg_color = themed_perfometer_bg_color

    @classmethod
    def type_name(cls) -> str:
        return "bidirectional"

    def get_stack(self) -> MetricRendererStack:
        projections = []

        if left_projections := _project_segments(
            _make_projection(
                perfometers_api.FocusRange(
                    perfometers_api.Closed(0),
                    self.perfometer.left.focus_range.upper,
                ),
                self._PROJECTION_PARAMETERS,
                self.translated_metrics,
                self.perfometer.name,
            ),
            _evaluate_segments(
                self.perfometer.left.segments,
                self.translated_metrics,
            ),
            self._PROJECTION_PARAMETERS.perfometer_full_at,
            self.themed_perfometer_bg_color,
        ):
            projections.extend(left_projections[::-1])

        if right_projections := _project_segments(
            _make_projection(
                perfometers_api.FocusRange(
                    perfometers_api.Closed(0),
                    self.perfometer.right.focus_range.upper,
                ),
                self._PROJECTION_PARAMETERS,
                self.translated_metrics,
                self.perfometer.name,
            ),
            _evaluate_segments(
                self.perfometer.right.segments,
                self.translated_metrics,
            ),
            self._PROJECTION_PARAMETERS.perfometer_full_at,
            self.themed_perfometer_bg_color,
        ):
            projections.extend(right_projections)

        return [projections] if projections else []

    def get_label(self) -> str:
        labels = []

        if left_label := _get_renderer(self.perfometer.left, self.translated_metrics).get_label():
            labels.append(left_label)

        if right_label := _get_renderer(self.perfometer.right, self.translated_metrics).get_label():
            labels.append(right_label)

        return " / ".join(labels)

    def get_sort_value(self) -> float:
        return max(
            [
                _get_renderer(self.perfometer.left, self.translated_metrics).get_sort_value(),
                _get_renderer(self.perfometer.right, self.translated_metrics).get_sort_value(),
            ]
        )


class MetricometerRendererStacked(MetricometerRenderer):
    def __init__(
        self,
        perfometer: perfometers_api.Stacked,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        # Needed for sorting via cmk/gui/views/perfometers/base.py::sort_value::_get_metrics_sort_group
        self.perfometer = perfometer
        self.translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "stacked"

    def get_stack(self) -> MetricRendererStack:
        projections: list[Sequence[tuple[float, str]]] = []

        if upper_projections := _get_renderer(
            self.perfometer.upper, self.translated_metrics
        ).get_stack():
            projections.append(upper_projections[0])

        if lower_projections := _get_renderer(
            self.perfometer.lower, self.translated_metrics
        ).get_stack():
            projections.append(lower_projections[0])

        return projections if projections else []

    def get_label(self) -> str:
        labels = []

        if upper_label := _get_renderer(self.perfometer.upper, self.translated_metrics).get_label():
            labels.append(upper_label)

        if lower_label := _get_renderer(self.perfometer.lower, self.translated_metrics).get_label():
            labels.append(lower_label)

        return " / ".join(labels)

    def get_sort_value(self) -> float:
        return _get_renderer(self.perfometer.upper, self.translated_metrics).get_sort_value()


def _get_renderer(
    perfometer: (
        perfometers_api.Perfometer | perfometers_api.Bidirectional | perfometers_api.Stacked
    ),
    translated_metrics: Mapping[str, TranslatedMetric],
) -> (
    MetricometerRendererPerfometer | MetricometerRendererBidirectional | MetricometerRendererStacked
):
    match perfometer:
        case perfometers_api.Perfometer():
            return MetricometerRendererPerfometer(
                perfometer,
                translated_metrics,
                get_themed_perfometer_bg_color(),
            )
        case perfometers_api.Bidirectional():
            return MetricometerRendererBidirectional(
                perfometer,
                translated_metrics,
                get_themed_perfometer_bg_color(),
            )
        case perfometers_api.Stacked():
            return MetricometerRendererStacked(perfometer, translated_metrics)


def get_first_matching_perfometer(
    translated_metrics: Mapping[str, TranslatedMetric],
    registered_perfometers: Mapping[
        str, perfometers_api.Perfometer | perfometers_api.Bidirectional | perfometers_api.Stacked
    ],
) -> (
    MetricometerRendererPerfometer
    | MetricometerRendererBidirectional
    | MetricometerRendererStacked
    | None
):
    if not translated_metrics:
        return None

    for perfometer in registered_perfometers.values():
        if _perfometer_matches(perfometer, translated_metrics):
            return _get_renderer(perfometer, translated_metrics)

    return None
