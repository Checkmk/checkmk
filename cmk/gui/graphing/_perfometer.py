#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import math
from collections.abc import Sequence
from typing import Any, Callable, Literal, NotRequired, TypeAlias, TypedDict

from cmk.utils import plugin_registry
from cmk.utils.exceptions import MKGeneralException

from cmk.gui.exceptions import MKInternalError
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.type_defs import TranslatedMetrics, UnitInfo
from cmk.gui.view_utils import get_themed_perfometer_bg_color

from ._expression import (
    ConstantFloat,
    ConstantInt,
    has_required_metrics_or_scalars,
    parse_conditional_expression,
    parse_expression,
)
from ._unit_info import unit_info

LegacyPerfometer = tuple[str, Any]


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
    perfometers: Sequence[_LinearPerfometerSpec | LogarithmicPerfometerSpec | _DualPerfometerSpec]


PerfometerSpec: TypeAlias = (
    _LinearPerfometerSpec | LogarithmicPerfometerSpec | _DualPerfometerSpec | _StackedPerfometerSpec
)
perfometer_info: list[LegacyPerfometer | PerfometerSpec] = []


def _parse_perfometers(perfometers: list[LegacyPerfometer | PerfometerSpec]) -> None:
    for index, perfometer in reversed(list(enumerate(perfometers))):
        if isinstance(perfometer, dict):
            continue

        if not isinstance(perfometer, tuple) or len(perfometer) != 2:
            raise MKGeneralException(_("Invalid perfometer declaration: %r") % perfometer)

        # Convert legacy tuple based perfometer
        perfometer_type, perfometer_args = perfometer[0], perfometer[1]
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
                _("Could not convert perfometer to dict format: %r. Ignoring this one."), perfometer
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
    perfometer: PerfometerSpec, translated_metrics: TranslatedMetrics
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
            [parse_expression(perfometer["metric"], translated_metrics)], translated_metrics
        )

    if perfometer["type"] in ("dual", "stacked"):
        return all(
            _perfometer_has_required_metrics_or_scalars(p, translated_metrics)
            for p in perfometer["perfometers"]
        )

    raise NotImplementedError(_("Invalid perfometer type: %s") % perfometer["type"])


def _perfometer_possible(perfometer: PerfometerSpec, translated_metrics: TranslatedMetrics) -> bool:
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


def get_first_matching_perfometer(translated_metrics: TranslatedMetrics) -> PerfometerSpec | None:
    for perfometer in perfometer_info:
        if not isinstance(perfometer, dict):
            continue
        if _perfometer_possible(perfometer, translated_metrics):
            return perfometer
    return None


MetricRendererStack = list[list[tuple[int | float, str]]]


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
        self, perfometer: PerfometerSpec, translated_metrics: TranslatedMetrics
    ) -> MetricometerRenderer:
        if perfometer["type"] == "logarithmic":
            return MetricometerRendererLogarithmic(perfometer, translated_metrics)
        if perfometer["type"] == "linear":
            return MetricometerRendererLinear(perfometer, translated_metrics)
        if perfometer["type"] == "dual":
            return MetricometerRendererDual(perfometer, translated_metrics)
        if perfometer["type"] == "stacked":
            return MetricometerRendererStacked(perfometer, translated_metrics)
        raise ValueError(perfometer["type"])


renderer_registry = MetricometerRendererRegistry()


@renderer_registry.register
class MetricometerRendererLogarithmic(MetricometerRenderer):
    def __init__(
        self,
        perfometer: LogarithmicPerfometerSpec,
        translated_metrics: TranslatedMetrics,
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
        return "logarithmic"

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


@renderer_registry.register
class MetricometerRendererLinear(MetricometerRenderer):
    def __init__(
        self,
        perfometer: _LinearPerfometerSpec,
        translated_metrics: TranslatedMetrics,
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
        return "linear"

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

        if isinstance(self._label_expression, (ConstantInt, ConstantFloat)):
            value = unit_info_.get("conversion", lambda v: v)(self._label_expression.value)
        else:
            value = result.value

        return self._render_value(unit_info_, value)

    def _evaluate_total(self) -> float:
        if isinstance(self._total.declaration, (ConstantInt, ConstantFloat)):
            return self._unit().get("conversion", lambda v: v)(self._total.declaration.value)
        return self._total.evaluate(self._translated_metrics).value

    def _unit(self) -> UnitInfo:
        # We assume that all expressions across all segments have the same unit
        return self._segments[0].evaluate(self._translated_metrics).unit_info

    def get_sort_value(self) -> float:
        """Use the first segment value for sorting"""
        return self._segments[0].evaluate(self._translated_metrics).value

    def _get_summed_values(self):
        return sum(segment.evaluate(self._translated_metrics).value for segment in self._segments)


@renderer_registry.register
class MetricometerRendererStacked(MetricometerRenderer):
    def __init__(
        self,
        perfometer: _StackedPerfometerSpec,
        translated_metrics: TranslatedMetrics,
    ) -> None:
        if len(perfometer["perfometers"]) != 2:
            raise MKInternalError(
                _("Perf-O-Meter of type 'dual' must contain exactly two definitions, not %d")
                % len(perfometer["perfometers"])
            )
        self._perfometers = perfometer["perfometers"]
        self._translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "stacked"

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


@renderer_registry.register
class MetricometerRendererDual(MetricometerRenderer):
    def __init__(
        self,
        perfometer: _DualPerfometerSpec,
        translated_metrics: TranslatedMetrics,
    ) -> None:
        if len(perfometer["perfometers"]) != 2:
            raise MKInternalError(
                _("Perf-O-Meter of type 'dual' must contain exactly two definitions, not %d")
                % len(perfometer["perfometers"])
            )
        self._perfometers = perfometer["perfometers"]
        self._translated_metrics = translated_metrics

    @classmethod
    def type_name(cls) -> str:
        return "dual"

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
