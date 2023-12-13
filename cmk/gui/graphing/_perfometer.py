#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable, Literal, NotRequired, TypeAlias, TypedDict

from cmk.utils import plugin_registry
from cmk.utils.exceptions import MKGeneralException

from cmk.gui.exceptions import MKInternalError
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.view_utils import get_themed_perfometer_bg_color

from cmk.graphing.v1 import metric, perfometer

from ._evaluate import evaluate_quantity, perfometer_matches
from ._expression import (
    Constant,
    has_required_metrics_or_scalars,
    parse_conditional_expression,
    parse_expression,
)
from ._loader import load_graphing_plugins
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


def _parse_perfometers(perfometers: list[LegacyPerfometer | PerfometerSpec]) -> None:
    for index, perfometer_ in reversed(list(enumerate(perfometers))):
        if isinstance(perfometer_, dict):
            continue

        if not isinstance(perfometer_, tuple) or len(perfometer_) != 2:
            raise MKGeneralException(_("Invalid perfometer declaration: %r") % perfometer_)

        # Convert legacy tuple based perfometer
        perfometer_type, perfometer_args = perfometer_[0], perfometer_[1]
        if perfometer_type == "dual":
            sub_performeters = perfometer_args[:]
            _parse_perfometers(sub_performeters)
            perfometers[index] = {
                "type": "dual",
                "perfometers": sub_performeters,
            }

        elif perfometer_type == "stacked":
            sub_performeters = perfometer_args[:]
            _parse_perfometers(sub_performeters)
            perfometers[index] = {
                "type": "stacked",
                "perfometers": sub_performeters,
            }

        elif perfometer_type == "linear" and len(perfometer_args) == 3:
            required, total, label = perfometer_args
            perfometers[index] = {
                "type": "linear",
                "segments": required,
                "total": total,
                "label": label,
            }

        else:
            logger.warning(
                _("Could not convert perfometer to dict format: %r. Ignoring this one."),
                perfometer_,
            )
            perfometers.pop(index)


def parse_perfometers(perfometers: list[LegacyPerfometer | PerfometerSpec]) -> None:
    # During implementation of the metric system the perfometers were first defined using
    # tuples. This has been replaced with a dict based syntax. This function converts the
    # old known formats from tuple to dict.
    # All shipped perfometers have been converted to the dict format with 1.5.0i3.
    # TODO: Remove this one day.
    _parse_perfometers(perfometers)


def _perfometer_has_required_metrics_or_scalars(
    perfometer_: PerfometerSpec, translated_metrics: Mapping[str, TranslatedMetric]
) -> bool:
    if perfometer_["type"] == "linear":
        expressions = [parse_expression(s, translated_metrics) for s in perfometer_["segments"]]
        if (total := perfometer_.get("total")) is not None:
            expressions.append(parse_expression(total, translated_metrics))
        if (label := perfometer_.get("label")) is not None:
            expressions.append(parse_expression(label[0], translated_metrics))
        return has_required_metrics_or_scalars(expressions, translated_metrics)

    if perfometer_["type"] == "logarithmic":
        return has_required_metrics_or_scalars(
            [parse_expression(perfometer_["metric"], translated_metrics)], translated_metrics
        )

    if perfometer_["type"] in ("dual", "stacked"):
        return all(
            _perfometer_has_required_metrics_or_scalars(p, translated_metrics)
            for p in perfometer_["perfometers"]
        )

    raise NotImplementedError(_("Invalid perfometer type: %s") % perfometer_["type"])


def _perfometer_possible(
    perfometer_: PerfometerSpec, translated_metrics: Mapping[str, TranslatedMetric]
) -> bool:
    if not translated_metrics:
        return False

    if not _perfometer_has_required_metrics_or_scalars(perfometer_, translated_metrics):
        return False

    if perfometer_["type"] == "linear":
        if "condition" in perfometer_:
            try:
                return parse_conditional_expression(
                    perfometer_["condition"], translated_metrics
                ).evaluate(translated_metrics)
            except Exception:
                return False

    return True


def get_first_matching_perfometer(
    translated_metrics: Mapping[str, TranslatedMetric]
) -> perfometer.Perfometer | perfometer.Bidirectional | perfometer.Stacked | PerfometerSpec | None:
    for perfometer_ in [
        plugin
        for plugin in load_graphing_plugins().plugins.values()
        if isinstance(
            plugin,
            (perfometer.Perfometer, perfometer.Bidirectional, perfometer.Stacked),
        )
    ]:
        if perfometer_matches(perfometer_, translated_metrics):
            return perfometer_

    # TODO CMK-15246 Checkmk 2.4: Remove legacy objects
    for legacy_perfometer in perfometer_info:
        if not isinstance(legacy_perfometer, dict):
            continue
        if _perfometer_possible(legacy_perfometer, translated_metrics):
            return legacy_perfometer
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
        perfometer_: perfometer.Perfometer
        | perfometer.Bidirectional
        | perfometer.Stacked
        | PerfometerSpec,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricometerRenderer:
        if isinstance(perfometer_, perfometer.Perfometer):
            return MetricometerRendererPerfometer(perfometer_, translated_metrics)
        if isinstance(perfometer_, perfometer.Bidirectional):
            return MetricometerRendererBidirectional(perfometer_, translated_metrics)
        if isinstance(perfometer_, perfometer.Stacked):
            return MetricometerRendererStacked(perfometer_, translated_metrics)
        if perfometer_["type"] == "logarithmic":
            return MetricometerRendererLegacyLogarithmic(perfometer_, translated_metrics)
        if perfometer_["type"] == "linear":
            return MetricometerRendererLegacyLinear(perfometer_, translated_metrics)
        if perfometer_["type"] == "dual":
            return MetricometerRendererLegacyDual(perfometer_, translated_metrics)
        if perfometer_["type"] == "stacked":
            return MetricometerRendererLegacyStacked(perfometer_, translated_metrics)
        raise ValueError(perfometer_["type"])


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


@dataclass(frozen=True)
class _ArcTan:
    x_shift: float
    y_shift: float
    stretch_factor: float

    @classmethod
    def from_parameters(
        cls,
        lower_x: float,
        upper_x: float,
        linear: _Linear,
        y_shift: float,
        scale: float,
    ) -> _ArcTan:
        return cls(
            (y_shift - linear.shift) / linear.slope,
            y_shift,
            scale * (upper_x - lower_x),
        )

    def __call__(self, value: int | float) -> float:
        return (
            30.0
            / math.pi
            * math.atan(math.pi / (30.0 * self.stretch_factor) * (value - self.x_shift))
            + self.y_shift
        )


def _raise(value: int | float) -> float:
    raise ValueError(value)


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
    scale: float


_PERFOMETER_PROJECTION_PARAMETERS = _ProjectionParameters(0.0, 15.0, 85.0, 100.0, 0.15)
_BIDIRECTIONAL_PROJECTION_PARAMETERS = _ProjectionParameters(0.0, 5.0, 45.0, 50.0, 0.03)


def _make_projection(
    focus_range: perfometer.FocusRange,
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

    match focus_range.lower, focus_range.upper:
        case perfometer.Closed(), perfometer.Closed():
            return _Projection(
                lower_x=lower_x,
                upper_x=upper_x,
                lower_atan=_raise,
                focus_linear=_Linear.from_points(
                    lower_x,
                    projection_parameters.lower_closed,
                    upper_x,
                    projection_parameters.upper_closed,
                ),
                upper_atan=_raise,
                limit=projection_parameters.upper_closed,
            )

        case perfometer.Open(), perfometer.Closed():
            linear = _Linear.from_points(
                lower_x,
                projection_parameters.lower_open,
                upper_x,
                projection_parameters.upper_closed,
            )
            return _Projection(
                lower_x=lower_x,
                upper_x=upper_x,
                lower_atan=_ArcTan.from_parameters(
                    lower_x,
                    upper_x,
                    linear,
                    projection_parameters.lower_open,
                    projection_parameters.scale,
                ),
                focus_linear=linear,
                upper_atan=_raise,
                limit=projection_parameters.upper_closed,
            )

        case perfometer.Closed(), perfometer.Open():
            linear = _Linear.from_points(
                lower_x,
                projection_parameters.lower_closed,
                upper_x,
                projection_parameters.upper_open,
            )
            return _Projection(
                lower_x=lower_x,
                upper_x=upper_x,
                lower_atan=_raise,
                focus_linear=linear,
                upper_atan=_ArcTan.from_parameters(
                    lower_x,
                    upper_x,
                    linear,
                    projection_parameters.upper_open,
                    projection_parameters.scale,
                ),
                limit=projection_parameters.upper_closed,
            )

        case perfometer.Open(), perfometer.Open():
            linear = _Linear.from_points(
                lower_x,
                projection_parameters.lower_open,
                upper_x,
                projection_parameters.upper_open,
            )
            return _Projection(
                lower_x=lower_x,
                upper_x=upper_x,
                lower_atan=_ArcTan.from_parameters(
                    lower_x,
                    upper_x,
                    linear,
                    projection_parameters.lower_open,
                    projection_parameters.scale,
                ),
                focus_linear=linear,
                upper_atan=_ArcTan.from_parameters(
                    lower_x,
                    upper_x,
                    linear,
                    projection_parameters.upper_open,
                    projection_parameters.scale,
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
        | metric.Constant
        | metric.WarningOf
        | metric.CriticalOf
        | metric.MinimumOf
        | metric.MaximumOf
        | metric.Sum
        | metric.Product
        | metric.Difference
        | metric.Fraction
    ],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> Sequence[_StackEntry]:
    return [
        _StackEntry(computed.value, computed.color)
        for segment in segments
        if (computed := evaluate_quantity(segment, translated_metrics)).value > 0
    ]


def _project_segments(
    projection: _Projection,
    segments: Sequence[_StackEntry],
) -> list[tuple[float, str]]:
    total = sum(s.value for s in segments)
    total_projection = projection(total)
    projections = [
        (
            round(total_projection * (entry.value / total), 2),
            entry.color,
        )
        for entry in segments
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
        perfometer_: perfometer.Perfometer,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        self.perfometer = perfometer_
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
        perfometer_: perfometer.Bidirectional,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        self.perfometer = perfometer_
        self.translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "bidirectional"

    def get_stack(self) -> MetricRendererStack:
        projections = []

        if left_projections := _project_segments(
            _make_projection(
                perfometer.FocusRange(
                    perfometer.Closed(0),
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
                perfometer.FocusRange(
                    perfometer.Closed(0),
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
        perfometer_: perfometer.Stacked,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        self.perfometer = perfometer_
        self.translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "stacked"

    def get_stack(self) -> MetricRendererStack:
        projections: list[Sequence[tuple[float, str]]] = []

        if lower_projections := renderer_registry.get_renderer(
            self.perfometer.lower,
            self.translated_metrics,
        ).get_stack():
            projections.append(lower_projections[0])

        if upper_projections := renderer_registry.get_renderer(
            self.perfometer.upper,
            self.translated_metrics,
        ).get_stack():
            projections.append(upper_projections[0])

        return projections if projections else []

    def get_label(self) -> str:
        labels = []

        if lower_label := renderer_registry.get_renderer(
            self.perfometer.lower,
            self.translated_metrics,
        ).get_label():
            labels.append(lower_label)

        if upper_label := renderer_registry.get_renderer(
            self.perfometer.upper,
            self.translated_metrics,
        ).get_label():
            labels.append(upper_label)

        return " / ".join(labels)

    def get_sort_value(self) -> float:
        return renderer_registry.get_renderer(
            self.perfometer.upper,
            self.translated_metrics,
        ).get_sort_value()


class MetricometerRendererLegacyLogarithmic(MetricometerRenderer):
    def __init__(
        self,
        perfometer_: LogarithmicPerfometerSpec,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        if "metric" not in perfometer_:
            raise MKGeneralException(
                _('Missing key "metric" in logarithmic perfometer: %r') % perfometer_
            )

        self._metric = parse_expression(perfometer_["metric"], translated_metrics)
        self._half_value = perfometer_["half_value"]
        self._exponent = perfometer_["exponent"]
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
        perfometer_: _LinearPerfometerSpec,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        self._segments = [parse_expression(s, translated_metrics) for s in perfometer_["segments"]]
        self._total = parse_expression(perfometer_["total"], translated_metrics)
        if (label := perfometer_.get("label")) is None:
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
        perfometer_: _StackedPerfometerSpec,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        if len(perfometer_["perfometers"]) != 2:
            raise MKInternalError(
                _("Perf-O-Meter of type 'dual' must contain exactly two definitions, not %d")
                % len(perfometer_["perfometers"])
            )
        self._perfometers = perfometer_["perfometers"]
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
        perfometer_: _DualPerfometerSpec,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> None:
        if len(perfometer_["perfometers"]) != 2:
            raise MKInternalError(
                _("Perf-O-Meter of type 'dual' must contain exactly two definitions, not %d")
                % len(perfometer_["perfometers"])
            )
        self._perfometers = perfometer_["perfometers"]
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
