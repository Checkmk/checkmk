#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import repeat
from typing import Any, Callable, Literal, NotRequired, TypeAlias, TypedDict

from cmk.utils import plugin_registry
from cmk.utils.exceptions import MKGeneralException

from cmk.gui.exceptions import MKInternalError
from cmk.gui.i18n import _
from cmk.gui.view_utils import get_themed_perfometer_bg_color

from cmk.graphing.v1 import metrics, perfometers

from ._evaluate import evaluate_quantity, perfometer_matches
from ._expression import (
    Constant,
    has_required_metrics_or_scalars,
    parse_conditional_expression,
    parse_expression,
)
from ._loader import perfometers_from_api
from ._type_defs import TranslatedMetric, UnitInfo
from ._unit_info import unit_info


class _LinearPerfometerSpec(TypedDict):
    type: Literal["linear"]
    segments: Sequence[str]
    total: int | float | str
    condition: NotRequired[str]
    label: NotRequired[tuple[str, str] | None]  # (expression, unit)


class LogarithmicPerfometerSpec(TypedDict):
    type: Literal["logarithmic"]
    metric: str
    half_value: int | float
    exponent: int | float


class _DualPerfometerSpec(TypedDict):
    type: Literal["dual"]
    perfometers: Sequence[_LinearPerfometerSpec | LogarithmicPerfometerSpec]


class _StackedPerfometerSpec(TypedDict):
    type: Literal["stacked"]
    perfometers: Sequence[_LinearPerfometerSpec | LogarithmicPerfometerSpec]


LegacyPerfometer = tuple[str, Any]
PerfometerSpec: TypeAlias = (
    _LinearPerfometerSpec | LogarithmicPerfometerSpec | _DualPerfometerSpec | _StackedPerfometerSpec
)
perfometer_info: list[LegacyPerfometer | PerfometerSpec] = []
MetricRendererStack = Sequence[Sequence[tuple[int | float, str]]]


def _parse_sub_perfometer(
    perfometer: LegacyPerfometer | PerfometerSpec,
) -> _LinearPerfometerSpec | LogarithmicPerfometerSpec:
    parsed = _parse_perfometer(perfometer)
    if parsed["type"] == "linear" or parsed["type"] == "logarithmic":
        return parsed
    raise MKGeneralException(
        _(
            "Dual or stacked Perf-O-Meters are not allowed to have"
            " 'dual' or 'stacked' sub Perf-O-Meters"
        )
    )


def _parse_perfometer(
    perfometer: LegacyPerfometer | PerfometerSpec,
) -> PerfometerSpec:
    if isinstance(perfometer, dict):
        return perfometer

    # During implementation of the metric system the perfometers were first defined using
    # tuples. This has been replaced with a dict based syntax. This function converts the
    # old known formats from tuple to dict.
    # All shipped perfometers have been converted to the dict format with 1.5.0i3.
    if not isinstance(perfometer, tuple) or len(perfometer) != 2:
        raise MKGeneralException(_("Invalid perfometer declaration: %r") % perfometer)

    # Convert legacy tuple based perfometer
    perfometer_type, perfometer_args = perfometer[0], perfometer[1]
    if perfometer_type == "dual":
        return _DualPerfometerSpec(
            type="dual",
            perfometers=[_parse_sub_perfometer(p) for p in perfometer_args],
        )

    if perfometer_type == "stacked":
        return _StackedPerfometerSpec(
            type="stacked",
            perfometers=[_parse_sub_perfometer(p) for p in perfometer_args],
        )

    if perfometer_type == "linear" and len(perfometer_args) == 3:
        return _LinearPerfometerSpec(
            type="linear",
            segments=perfometer_args[0],
            total=perfometer_args[1],
            label=perfometer_args[2],
        )

    raise MKGeneralException(
        _("Could not convert perfometer to dict format: %r. Ignoring this one.") % perfometer
    )


def parse_perfometer(
    perfometer: LegacyPerfometer | PerfometerSpec,
) -> PerfometerSpec:
    parsed = _parse_perfometer(perfometer)
    if parsed["type"] == "dual" and len(parsed["perfometers"]) != 2:
        raise MKGeneralException(
            _("Perf-O-Meter %r must contain exactly two definitions, not %d")
            % (parsed, len(parsed["perfometers"]))
        )
    return parsed


def _perfometer_has_required_metrics_or_scalars(
    perfometer: PerfometerSpec, translated_metrics: Mapping[str, TranslatedMetric]
) -> bool:
    if perfometer["type"] == "linear":
        expressions = [parse_expression(s, translated_metrics) for s in perfometer["segments"]]
        if (total := perfometer.get("total")) is not None:
            expressions.append(parse_expression(total, translated_metrics))
        if (label := perfometer.get("label")) is not None:
            expressions.append(parse_expression(label[0], translated_metrics))
        return has_required_metrics_or_scalars(expressions, translated_metrics)

    if perfometer["type"] == "logarithmic":
        return has_required_metrics_or_scalars(
            [parse_expression(perfometer["metric"], translated_metrics)],
            translated_metrics,
        )

    if perfometer["type"] in ("dual", "stacked"):
        return all(
            _perfometer_has_required_metrics_or_scalars(p, translated_metrics)
            for p in perfometer["perfometers"]
        )

    raise NotImplementedError(_("Invalid perfometer type: %s") % perfometer["type"])


def _perfometer_possible(
    perfometer: PerfometerSpec, translated_metrics: Mapping[str, TranslatedMetric]
) -> bool:
    if not translated_metrics:
        return False

    if not _perfometer_has_required_metrics_or_scalars(perfometer, translated_metrics):
        return False

    if perfometer["type"] == "linear":
        if "condition" in perfometer:
            try:
                return parse_conditional_expression(
                    perfometer["condition"], translated_metrics
                ).evaluate(translated_metrics)
            except Exception:
                return False

    return True


def get_first_matching_perfometer(
    translated_metrics: Mapping[str, TranslatedMetric],
) -> (
    perfometers.Perfometer | perfometers.Bidirectional | perfometers.Stacked | PerfometerSpec | None
):
    for perfometer in perfometers_from_api.values():
        if perfometer_matches(perfometer, translated_metrics):
            return perfometer

    # TODO CMK-15246 Checkmk 2.4: Remove legacy objects
    for legacy_perfometer in perfometer_info:
        parsed = parse_perfometer(legacy_perfometer)
        if _perfometer_possible(parsed, translated_metrics):
            return parsed
    return None


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
    def _render_value(unit: UnitInfo, value: float) -> str:
        return unit.get("perfometer_render", unit["render"])(value)


class MetricometerRendererRegistry(plugin_registry.Registry[type[MetricometerRenderer]]):
    def plugin_name(self, instance):
        return instance.type_name()

    def get_renderer(
        self,
        perfometer: (
            perfometers.Perfometer
            | perfometers.Bidirectional
            | perfometers.Stacked
            | PerfometerSpec
        ),
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricometerRenderer:
        if isinstance(perfometer, perfometers.Perfometer):
            return MetricometerRendererPerfometer(perfometer, translated_metrics)
        if isinstance(perfometer, perfometers.Bidirectional):
            return MetricometerRendererBidirectional(perfometer, translated_metrics)
        if isinstance(perfometer, perfometers.Stacked):
            return MetricometerRendererStacked(perfometer, translated_metrics)
        if perfometer["type"] == "logarithmic":
            return MetricometerRendererLegacyLogarithmic(perfometer, translated_metrics)
        if perfometer["type"] == "linear":
            return MetricometerRendererLegacyLinear(perfometer, translated_metrics)
        if perfometer["type"] == "dual":
            return MetricometerRendererLegacyDual(perfometer, translated_metrics)
        if perfometer["type"] == "stacked":
            return MetricometerRendererLegacyStacked(perfometer, translated_metrics)
        raise ValueError(perfometer["type"])


renderer_registry = MetricometerRendererRegistry()


@dataclass(frozen=True)
class _Linear:
    slope: float
    shift: float

    @classmethod
    def from_points(cls, lower_x: float, lower_y: float, upper_x: float, upper_y: float) -> _Linear:
        slope = (upper_y - lower_y) / (upper_x - lower_x)
        shift = -1.0 * slope * lower_x + lower_y
        return cls(slope, shift)

    def __call__(self, value: int | float) -> float:
        return self.slope * value + self.shift


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
    lower_x: float
    upper_x: float
    lower_atan: Callable[[int | float], float]
    focus_linear: Callable[[int | float], float]
    upper_atan: Callable[[int | float], float]
    limit: float

    def __call__(self, value: int | float) -> float:
        if value < self.lower_x:
            return self.lower_atan(value)
        if value > self.upper_x:
            return self.upper_atan(value)
        return self.focus_linear(value)


@dataclass(frozen=True)
class _ProjectionParameters:
    lower_closed: float
    lower_open: float
    upper_open: float
    upper_closed: float


_PERFOMETER_PROJECTION_PARAMETERS = _ProjectionParameters(0.0, 15.0, 85.0, 100.0)
_BIDIRECTIONAL_PROJECTION_PARAMETERS = _ProjectionParameters(0.0, 5.0, 45.0, 50.0)


def _make_projection(
    focus_range: perfometers.FocusRange,
    projection_parameters: _ProjectionParameters,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> _Projection:
    if isinstance(focus_range.lower.value, (int, float)):
        lower_x = float(focus_range.lower.value)
    else:
        lower_x = evaluate_quantity(focus_range.lower.value, translated_metrics).value

    if isinstance(focus_range.upper.value, (int, float)):
        upper_x = float(focus_range.upper.value)
    else:
        upper_x = evaluate_quantity(focus_range.upper.value, translated_metrics).value

    if lower_x > upper_x:
        raise ValueError((lower_x, upper_x))

    # Note: if we have closed boundaries and a value exceeds the lower or upper limit then we use
    # the related limit. With this the value is always visible, we don't have any execption and the
    # perfometer is not filled resp. completely filled.
    match focus_range.lower, focus_range.upper:
        case perfometers.Closed(), perfometers.Closed():
            return _Projection(
                lower_x=lower_x,
                upper_x=upper_x,
                lower_atan=lambda v: lower_x,
                focus_linear=_Linear.from_points(
                    lower_x,
                    projection_parameters.lower_closed,
                    upper_x,
                    projection_parameters.upper_closed,
                ),
                upper_atan=lambda v: upper_x,
                limit=projection_parameters.upper_closed,
            )

        case perfometers.Open(), perfometers.Closed():
            linear = _Linear.from_points(
                lower_x,
                projection_parameters.lower_open,
                upper_x,
                projection_parameters.upper_closed,
            )
            return _Projection(
                lower_x=lower_x,
                upper_x=upper_x,
                lower_atan=_ArcTan(
                    x_inflection=lower_x,
                    y_inflection=projection_parameters.lower_open,
                    slope_inflection=linear.slope,
                    scale_in_units_of_pi_half=projection_parameters.lower_open
                    - projection_parameters.lower_closed,
                ),
                focus_linear=linear,
                upper_atan=lambda v: upper_x,
                limit=projection_parameters.upper_closed,
            )

        case perfometers.Closed(), perfometers.Open():
            linear = _Linear.from_points(
                lower_x,
                projection_parameters.lower_closed,
                upper_x,
                projection_parameters.upper_open,
            )
            return _Projection(
                lower_x=lower_x,
                upper_x=upper_x,
                lower_atan=lambda v: lower_x,
                focus_linear=linear,
                upper_atan=_ArcTan(
                    x_inflection=upper_x,
                    y_inflection=projection_parameters.upper_open,
                    slope_inflection=linear.slope,
                    scale_in_units_of_pi_half=projection_parameters.upper_closed
                    - projection_parameters.upper_open,
                ),
                limit=projection_parameters.upper_closed,
            )

        case perfometers.Open(), perfometers.Open():
            linear = _Linear.from_points(
                lower_x,
                projection_parameters.lower_open,
                upper_x,
                projection_parameters.upper_open,
            )
            return _Projection(
                lower_x=lower_x,
                upper_x=upper_x,
                lower_atan=_ArcTan(
                    x_inflection=lower_x,
                    y_inflection=projection_parameters.lower_open,
                    slope_inflection=linear.slope,
                    scale_in_units_of_pi_half=projection_parameters.lower_open
                    - projection_parameters.lower_closed,
                ),
                focus_linear=linear,
                upper_atan=_ArcTan(
                    x_inflection=upper_x,
                    y_inflection=projection_parameters.upper_open,
                    slope_inflection=linear.slope,
                    scale_in_units_of_pi_half=projection_parameters.upper_closed
                    - projection_parameters.upper_open,
                ),
                limit=projection_parameters.upper_closed,
            )

    assert False, focus_range


@dataclass(frozen=True)
class _StackEntry:
    value: float
    color: str


def _compute_segments(
    segments: Sequence[
        str
        | metrics.Constant
        | metrics.WarningOf
        | metrics.CriticalOf
        | metrics.MinimumOf
        | metrics.MaximumOf
        | metrics.Sum
        | metrics.Product
        | metrics.Difference
        | metrics.Fraction
    ],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Sequence[_StackEntry]:
    return [
        _StackEntry(computed.value, computed.color)
        for segment in segments
        if (computed := evaluate_quantity(segment, translated_metrics))
    ]


def _project_segments(
    projection: _Projection,
    segments: Sequence[_StackEntry],
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
            round(projection.limit - sum(p[0] for p in projections), 2),
            get_themed_perfometer_bg_color(),
        )
    )
    return projections


class MetricometerRendererPerfometer(MetricometerRenderer):
    def __init__(
        self,
        perfometer: perfometers.Perfometer,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        self.perfometer = perfometer
        self.translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "perfometer"

    def get_stack(self) -> MetricRendererStack:
        if projections := _project_segments(
            _make_projection(
                self.perfometer.focus_range,
                _PERFOMETER_PROJECTION_PARAMETERS,
                self.translated_metrics,
            ),
            _compute_segments(
                self.perfometer.segments,
                self.translated_metrics,
            ),
        ):
            return [projections]
        return []

    def get_label(self) -> str:
        first_segment = evaluate_quantity(self.perfometer.segments[0], self.translated_metrics)
        return first_segment.unit["render"](
            first_segment.value
            + sum(
                (
                    evaluate_quantity(s, self.translated_metrics).value
                    for s in self.perfometer.segments[1:]
                )
            )
        )

    def get_sort_value(self) -> float:
        return sum(
            (evaluate_quantity(s, self.translated_metrics).value for s in self.perfometer.segments)
        )


class MetricometerRendererBidirectional(MetricometerRenderer):
    def __init__(
        self,
        perfometer: perfometers.Bidirectional,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        self.perfometer = perfometer
        self.translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "bidirectional"

    def get_stack(self) -> MetricRendererStack:
        projections = []

        if left_projections := _project_segments(
            _make_projection(
                perfometers.FocusRange(
                    perfometers.Closed(0),
                    self.perfometer.left.focus_range.upper,
                ),
                _BIDIRECTIONAL_PROJECTION_PARAMETERS,
                self.translated_metrics,
            ),
            _compute_segments(
                self.perfometer.left.segments,
                self.translated_metrics,
            ),
        ):
            projections.extend(left_projections[::-1])

        if right_projections := _project_segments(
            _make_projection(
                perfometers.FocusRange(
                    perfometers.Closed(0),
                    self.perfometer.right.focus_range.upper,
                ),
                _BIDIRECTIONAL_PROJECTION_PARAMETERS,
                self.translated_metrics,
            ),
            _compute_segments(
                self.perfometer.right.segments,
                self.translated_metrics,
            ),
        ):
            projections.extend(right_projections)

        return [projections] if projections else []

    def get_label(self) -> str:
        labels = []

        if left_label := renderer_registry.get_renderer(
            self.perfometer.left,
            self.translated_metrics,
        ).get_label():
            labels.append(left_label)

        if right_label := renderer_registry.get_renderer(
            self.perfometer.right,
            self.translated_metrics,
        ).get_label():
            labels.append(right_label)

        return " / ".join(labels)

    def get_sort_value(self) -> float:
        return max(
            [
                renderer_registry.get_renderer(
                    self.perfometer.left,
                    self.translated_metrics,
                ).get_sort_value(),
                renderer_registry.get_renderer(
                    self.perfometer.right,
                    self.translated_metrics,
                ).get_sort_value(),
            ]
        )


class MetricometerRendererStacked(MetricometerRenderer):
    def __init__(
        self,
        perfometer: perfometers.Stacked,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        self.perfometer = perfometer
        self.translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "stacked"

    def get_stack(self) -> MetricRendererStack:
        projections: list[Sequence[tuple[float, str]]] = []

        if upper_projections := renderer_registry.get_renderer(
            self.perfometer.upper,
            self.translated_metrics,
        ).get_stack():
            projections.append(upper_projections[0])

        if lower_projections := renderer_registry.get_renderer(
            self.perfometer.lower,
            self.translated_metrics,
        ).get_stack():
            projections.append(lower_projections[0])

        return projections if projections else []

    def get_label(self) -> str:
        labels = []

        if upper_label := renderer_registry.get_renderer(
            self.perfometer.upper,
            self.translated_metrics,
        ).get_label():
            labels.append(upper_label)

        if lower_label := renderer_registry.get_renderer(
            self.perfometer.lower,
            self.translated_metrics,
        ).get_label():
            labels.append(lower_label)

        return " / ".join(labels)

    def get_sort_value(self) -> float:
        return renderer_registry.get_renderer(
            self.perfometer.upper,
            self.translated_metrics,
        ).get_sort_value()


class MetricometerRendererLegacyLogarithmic(MetricometerRenderer):
    def __init__(
        self,
        perfometer: LogarithmicPerfometerSpec,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        if "metric" not in perfometer:
            raise MKGeneralException(
                _('Missing key "metric" in logarithmic perfometer: %r') % perfometer
            )

        self._metric = parse_expression(perfometer["metric"], translated_metrics)
        self._half_value = perfometer["half_value"]
        self._exponent = perfometer["exponent"]
        self._translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "legacy_logarithmic"

    def get_stack(self) -> MetricRendererStack:
        result = self._metric.evaluate(self._translated_metrics)
        return [
            self.get_stack_from_values(
                result.value,
                *self.estimate_parameters_for_converted_units(
                    result.unit_info.get(
                        "conversion",
                        lambda v: v,
                    )
                ),
                result.color,
            )
        ]

    def get_label(self) -> str:
        result = self._metric.evaluate(self._translated_metrics)
        return self._render_value(result.unit_info, result.value)

    def get_sort_value(self) -> float:
        """Returns the number to sort this perfometer with compared to the other
        performeters in the current performeter sort group"""
        return self._metric.evaluate(self._translated_metrics).value

    @staticmethod
    def get_stack_from_values(
        value: str | int | float,
        half_value: int | float,
        base: int | float,
        color: str,
    ) -> list[tuple[int | float, str]]:
        """
        half_value: if value == half_value, the perfometer is filled by 50%
        base: if we multiply value by base, the perfometer is filled by another 10%, unless we hit
        the min/max cutoffs
        """
        # Negative values are printed like positive ones (e.g. time offset)
        value = abs(float(value))
        if value == 0.0:
            pos = 0.0
        else:
            half_value = float(half_value)
            h = math.log(half_value, base)  # value to be displayed at 50%
            pos = 50 + 10.0 * (math.log(value, base) - h)
            pos = min(max(2, pos), 98)

        return [(pos, color), (100 - pos, get_themed_perfometer_bg_color())]

    def estimate_parameters_for_converted_units(
        self, conversion: Callable[[float], float]
    ) -> tuple[float, float]:
        """
        Estimate a new half_value (50%-value) and a new exponent (10%-factor) for converted units.

        Regarding the 50%-value, we can simply apply the conversion. However, regarding the 10%-
        factor, it's certainly wrong to simply directly apply the conversion. For example, doing
        that for the conversion degree celsius -> degree fahrenheit would yield a 10%-factor of 28.5
        for degree fahrenheit (compared to 1.2 for degree celsius).

        Instead, we estimate a new factor as follows:
        h_50: 50%-value for original units
        f_10: 10%-factor for original units
        c: conversion function
        h_50_c = c(h_50): 50%-value for converted units aka. converted 50%-value
        f_10_c: 10%-factor for converted units

        f_10_c = c(h_50 * f_10) / h_50_c
                 --------------
                 converted 60%-value
                 -----------------------
                 ratio of converted 60%- to converted 50%-value
        """
        h_50 = self._half_value
        f_10 = self._exponent
        h_50_c = conversion(self._half_value)
        return (
            h_50_c,
            conversion(h_50 * f_10) / h_50_c,
        )


class MetricometerRendererLegacyLinear(MetricometerRenderer):
    def __init__(
        self,
        perfometer: _LinearPerfometerSpec,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        self._segments = [parse_expression(s, translated_metrics) for s in perfometer["segments"]]
        self._total = parse_expression(perfometer["total"], translated_metrics)
        if (label := perfometer.get("label")) is None:
            self._label_expression = None
            self._label_unit_name = None
        else:
            self._label_expression = parse_expression(label[0], translated_metrics)
            self._label_unit_name = label[1]
        self._translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "legacy_linear"

    def get_stack(self) -> MetricRendererStack:
        entry = []

        summed = self._get_summed_values()

        if (total := self._evaluate_total()) == 0:
            entry.append((100.0, get_themed_perfometer_bg_color()))
        else:
            for segment in self._segments:
                result = segment.evaluate(self._translated_metrics)
                entry.append((100.0 * result.value / total, result.color))

            # Paint rest only, if it is positive and larger than one promille
            if total - summed > 0.001:
                entry.append((100.0 * (total - summed) / total, get_themed_perfometer_bg_color()))

        return [entry]

    def get_label(self) -> str:
        # "label" option in all Perf-O-Meters overrides automatic label
        if self._label_expression is None:
            return self._render_value(self._unit(), self._get_summed_values())

        result = self._label_expression.evaluate(self._translated_metrics)
        unit_info_ = unit_info[self._label_unit_name] if self._label_unit_name else result.unit_info

        if isinstance(self._label_expression, Constant):
            value = unit_info_.get("conversion", lambda v: v)(self._label_expression.value)
        else:
            value = result.value

        return self._render_value(unit_info_, value)

    def _evaluate_total(self) -> float:
        if isinstance(self._total, Constant):
            return self._unit().get("conversion", lambda v: v)(self._total.value)
        return self._total.evaluate(self._translated_metrics).value

    def _unit(self) -> UnitInfo:
        # We assume that all expressions across all segments have the same unit
        return self._segments[0].evaluate(self._translated_metrics).unit_info

    def get_sort_value(self) -> float:
        """Use the first segment value for sorting"""
        return self._segments[0].evaluate(self._translated_metrics).value

    def _get_summed_values(self):
        return sum(segment.evaluate(self._translated_metrics).value for segment in self._segments)


class MetricometerRendererLegacyStacked(MetricometerRenderer):
    def __init__(
        self,
        perfometer: _StackedPerfometerSpec,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        self._perfometers = perfometer["perfometers"]
        self._translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "legacy_stacked"

    def get_stack(self) -> MetricRendererStack:
        stack = []
        for sub_perfometer in self._perfometers:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_stack = renderer.get_stack()
            stack.append(sub_stack[0])

        return stack

    def get_label(self) -> str:
        sub_labels = []
        for sub_perfometer in self._perfometers:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_label = renderer.get_label()
            if sub_label:
                sub_labels.append(sub_label)

        if not sub_labels:
            return ""

        return " / ".join(sub_labels)

    def get_sort_value(self) -> float:
        """Use the number of the first stack element."""
        sub_perfometer = self._perfometers[0]
        renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)
        return renderer.get_sort_value()


class MetricometerRendererLegacyDual(MetricometerRenderer):
    def __init__(
        self,
        perfometer: _DualPerfometerSpec,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        self._perfometers = perfometer["perfometers"]
        self._translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "legacy_dual"

    def get_stack(self) -> MetricRendererStack:
        content: list[tuple[int | float, str]] = []
        for nr, sub_perfometer in enumerate(self._perfometers):
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_stack = renderer.get_stack()
            if len(sub_stack) != 1:
                raise MKInternalError(
                    _("Perf-O-Meter of type 'dual' must only contain plain Perf-O-Meters")
                )

            half_stack = [(int(value / 2.0), color) for (value, color) in sub_stack[0]]
            if nr == 0:
                half_stack.reverse()
            content += half_stack

        return [content]

    def get_label(self) -> str:
        sub_labels = []
        for sub_perfometer in self._perfometers:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)

            sub_label = renderer.get_label()
            if sub_label:
                sub_labels.append(sub_label)

        if not sub_labels:
            return ""

        return " / ".join(sub_labels)

    def get_sort_value(self) -> float:
        """Sort by max(left, right)

        E.g. for traffic graphs it seems to be useful to
        make it sort by the maximum traffic independent of the direction.
        """
        sub_sort_values = []
        for sub_perfometer in self._perfometers:
            renderer = renderer_registry.get_renderer(sub_perfometer, self._translated_metrics)
            sub_sort_values.append(renderer.get_sort_value())

        return max(*sub_sort_values)


def register() -> None:
    renderer_registry.register(MetricometerRendererPerfometer)
    renderer_registry.register(MetricometerRendererBidirectional)
    renderer_registry.register(MetricometerRendererStacked)
    # Legacy
    renderer_registry.register(MetricometerRendererLegacyLogarithmic)
    renderer_registry.register(MetricometerRendererLegacyLinear)
    renderer_registry.register(MetricometerRendererLegacyStacked)
    renderer_registry.register(MetricometerRendererLegacyDual)
