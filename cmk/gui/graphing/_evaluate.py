#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Self

from cmk.gui.i18n import _
from cmk.gui.utils.speaklater import LazyString

from cmk.graphing.v1 import Color
from cmk.graphing.v1 import metric as metric_api
from cmk.graphing.v1 import perfometer as perfometer_api

from ._parser import make_hex_color, make_unit_info
from ._type_defs import TranslatedMetric, UnitInfo


@dataclass(frozen=True)
class _MetricNamesOrScalars:
    _metric_names: list[metric_api.Name]
    _scalars: list[
        metric_api.WarningOf | metric_api.CriticalOf | metric_api.MinimumOf | metric_api.MaximumOf
    ]

    def collect_quantity_names(self, quantity: metric_api.Quantity) -> None:
        match quantity:
            case metric_api.Name():
                self._metric_names.append(quantity)
            case metric_api.WarningOf():
                self._metric_names.append(quantity.name)
                self._scalars.append(quantity)
            case metric_api.CriticalOf():
                self._metric_names.append(quantity.name)
                self._scalars.append(quantity)
            case metric_api.MinimumOf():
                self._metric_names.append(quantity.name)
                self._scalars.append(quantity)
            case metric_api.MaximumOf():
                self._metric_names.append(quantity.name)
                self._scalars.append(quantity)
            case metric_api.Sum():
                for s in quantity.summands:
                    self.collect_quantity_names(s)
            case metric_api.Product():
                for f in quantity.factors:
                    self.collect_quantity_names(f)
            case metric_api.Difference():
                self.collect_quantity_names(quantity.minuend)
                self.collect_quantity_names(quantity.subtrahend)
            case metric_api.Fraction():
                self.collect_quantity_names(quantity.dividend)
                self.collect_quantity_names(quantity.divisor)

    @classmethod
    def from_perfometers(cls, *perfometers: perfometer_api.Perfometer) -> Self:
        instance = cls([], [])
        for perfometer in perfometers:
            if not isinstance(perfometer.focus_range.lower.value, (int, float)):
                instance.collect_quantity_names(perfometer.focus_range.lower.value)
            if not isinstance(perfometer.focus_range.upper.value, (int, float)):
                instance.collect_quantity_names(perfometer.focus_range.upper.value)
            for s in perfometer.segments:
                instance.collect_quantity_names(s)
        return instance

    @property
    def metric_names(self) -> Sequence[metric_api.Name]:
        return self._metric_names

    @property
    def scalars(
        self,
    ) -> Sequence[
        metric_api.WarningOf | metric_api.CriticalOf | metric_api.MinimumOf | metric_api.MaximumOf
    ]:
        return self._scalars


def _scalar_name(
    scalar: metric_api.WarningOf
    | metric_api.CriticalOf
    | metric_api.MinimumOf
    | metric_api.MaximumOf,
) -> Literal["warn", "crit", "min", "max"]:
    match scalar:
        case metric_api.WarningOf():
            return "warn"
        case metric_api.CriticalOf():
            return "crit"
        case metric_api.MinimumOf():
            return "min"
        case metric_api.MaximumOf():
            return "max"


def _is_perfometer_applicable(
    translated_metrics: Mapping[str, TranslatedMetric],
    metric_names_or_scalars: _MetricNamesOrScalars,
) -> bool:
    if not (translated_metrics and metric_names_or_scalars.metric_names):
        return False
    for metric_name in metric_names_or_scalars.metric_names:
        if metric_name.value not in translated_metrics:
            return False
    for scalar in metric_names_or_scalars.scalars:
        if scalar.name.value not in translated_metrics:
            return False
        if _scalar_name(scalar) not in translated_metrics[scalar.name.value].get("scalar", {}):
            return False
    return True


def perfometer_matches(
    perfometer: perfometer_api.Perfometer | perfometer_api.Bidirectional | perfometer_api.Stacked,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> bool:
    match perfometer:
        case perfometer_api.Perfometer():
            metric_names_or_scalars = _MetricNamesOrScalars.from_perfometers(perfometer)
        case perfometer_api.Bidirectional():
            metric_names_or_scalars = _MetricNamesOrScalars.from_perfometers(
                perfometer.left,
                perfometer.right,
            )
        case perfometer_api.Stacked():
            metric_names_or_scalars = _MetricNamesOrScalars.from_perfometers(
                perfometer.lower,
                perfometer.upper,
            )
    return _is_perfometer_applicable(translated_metrics, metric_names_or_scalars)


@dataclass(frozen=True)
class EvaluatedQuantity:
    title: LazyString | str
    unit: UnitInfo
    color: str
    value: int | float


def evaluate_quantity(
    quantity: metric_api.Quantity,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> EvaluatedQuantity:
    match quantity:
        case metric_api.Name():
            metric = translated_metrics[quantity.value]
            return EvaluatedQuantity(
                metric["title"],
                metric["unit"],
                metric["color"],
                translated_metrics[quantity.value]["value"],
            )
        case metric_api.Constant():
            return EvaluatedQuantity(
                str(quantity.title),
                make_unit_info(quantity.unit),
                make_hex_color(quantity.color),
                quantity.value,
            )
        case metric_api.WarningOf():
            metric = translated_metrics[quantity.name.value]
            return EvaluatedQuantity(
                _("Warning of ") + metric["title"],
                metric["unit"],
                make_hex_color(Color.YELLOW),
                translated_metrics[quantity.name.value]["scalar"]["warn"],
            )
        case metric_api.CriticalOf():
            metric = translated_metrics[quantity.name.value]
            return EvaluatedQuantity(
                _("Critical of ") + metric["title"],
                metric["unit"],
                make_hex_color(Color.RED),
                translated_metrics[quantity.name.value]["scalar"]["crit"],
            )
        case metric_api.MinimumOf():
            metric = translated_metrics[quantity.name.value]
            return EvaluatedQuantity(
                _("Minimum of ") + metric["title"],
                metric["unit"],
                make_hex_color(quantity.color),
                translated_metrics[quantity.name.value]["scalar"]["min"],
            )
        case metric_api.MaximumOf():
            metric = translated_metrics[quantity.name.value]
            return EvaluatedQuantity(
                _("Maximum of ") + metric["title"],
                metric["unit"],
                make_hex_color(quantity.color),
                translated_metrics[quantity.name.value]["scalar"]["max"],
            )
        case metric_api.Sum():
            evaluated_first_summand = evaluate_quantity(quantity.summands[0], translated_metrics)
            return EvaluatedQuantity(
                str(quantity.title),
                evaluated_first_summand.unit,
                make_hex_color(quantity.color),
                (
                    evaluated_first_summand.value
                    + sum(
                        evaluate_quantity(s, translated_metrics).value
                        for s in quantity.summands[1:]
                    )
                ),
            )
        case metric_api.Product():
            product = 1.0
            for f in quantity.factors:
                product *= evaluate_quantity(f, translated_metrics).value
            return EvaluatedQuantity(
                str(quantity.title),
                make_unit_info(quantity.unit),
                make_hex_color(quantity.color),
                product,
            )
        case metric_api.Difference():
            evaluated_minuend = evaluate_quantity(quantity.minuend, translated_metrics)
            evaluated_subtrahend = evaluate_quantity(quantity.subtrahend, translated_metrics)
            return EvaluatedQuantity(
                str(quantity.title),
                evaluated_minuend.unit,
                make_hex_color(quantity.color),
                evaluated_minuend.value - evaluated_subtrahend.value,
            )
        case metric_api.Fraction():
            return EvaluatedQuantity(
                str(quantity.title),
                make_unit_info(quantity.unit),
                make_hex_color(quantity.color),
                (
                    evaluate_quantity(quantity.dividend, translated_metrics).value
                    / evaluate_quantity(quantity.divisor, translated_metrics).value
                ),
            )
