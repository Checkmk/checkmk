#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Self

from cmk.gui.i18n import _
from cmk.gui.utils.speaklater import LazyString

from cmk.graphing.v1 import metric, perfometer

from ._parser import parse_color, parse_unit
from ._type_defs import TranslatedMetric, UnitInfo


@dataclass(frozen=True)
class _MetricNamesOrScalars:
    _metric_names: list[str]
    _scalars: list[metric.WarningOf | metric.CriticalOf | metric.MinimumOf | metric.MaximumOf]

    def collect_quantity_names(
        self,
        quantity: (
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
        ),
    ) -> None:
        match quantity:
            case str():
                self._metric_names.append(quantity)
            case metric.WarningOf():
                self._metric_names.append(quantity.name)
                self._scalars.append(quantity)
            case metric.CriticalOf():
                self._metric_names.append(quantity.name)
                self._scalars.append(quantity)
            case metric.MinimumOf():
                self._metric_names.append(quantity.name)
                self._scalars.append(quantity)
            case metric.MaximumOf():
                self._metric_names.append(quantity.name)
                self._scalars.append(quantity)
            case metric.Sum():
                for s in quantity.summands:
                    self.collect_quantity_names(s)
            case metric.Product():
                for f in quantity.factors:
                    self.collect_quantity_names(f)
            case metric.Difference():
                self.collect_quantity_names(quantity.minuend)
                self.collect_quantity_names(quantity.subtrahend)
            case metric.Fraction():
                self.collect_quantity_names(quantity.dividend)
                self.collect_quantity_names(quantity.divisor)

    @classmethod
    def from_perfometers(cls, *perfometers: perfometer.Perfometer) -> Self:
        instance = cls([], [])
        for perfometer_ in perfometers:
            if not isinstance(perfometer_.focus_range.lower.value, (int, float)):
                instance.collect_quantity_names(perfometer_.focus_range.lower.value)
            if not isinstance(perfometer_.focus_range.upper.value, (int, float)):
                instance.collect_quantity_names(perfometer_.focus_range.upper.value)
            for s in perfometer_.segments:
                instance.collect_quantity_names(s)
        return instance

    @property
    def metric_names(self) -> Sequence[str]:
        return self._metric_names

    @property
    def scalars(
        self,
    ) -> Sequence[metric.WarningOf | metric.CriticalOf | metric.MinimumOf | metric.MaximumOf]:
        return self._scalars


def _scalar_name(
    scalar: metric.WarningOf | metric.CriticalOf | metric.MinimumOf | metric.MaximumOf,
) -> Literal["warn", "crit", "min", "max"]:
    match scalar:
        case metric.WarningOf():
            return "warn"
        case metric.CriticalOf():
            return "crit"
        case metric.MinimumOf():
            return "min"
        case metric.MaximumOf():
            return "max"


def _is_perfometer_applicable(
    translated_metrics: Mapping[str, TranslatedMetric],
    metric_names_or_scalars: _MetricNamesOrScalars,
) -> bool:
    if not (translated_metrics and metric_names_or_scalars.metric_names):
        return False
    for metric_name in metric_names_or_scalars.metric_names:
        if metric_name not in translated_metrics:
            return False
    for scalar in metric_names_or_scalars.scalars:
        if scalar.name not in translated_metrics:
            return False
        if _scalar_name(scalar) not in translated_metrics[scalar.name].get("scalar", {}):
            return False
    return True


def perfometer_matches(
    perfometer_: perfometer.Perfometer | perfometer.Bidirectional | perfometer.Stacked,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> bool:
    match perfometer_:
        case perfometer.Perfometer():
            metric_names_or_scalars = _MetricNamesOrScalars.from_perfometers(perfometer_)
        case perfometer.Bidirectional():
            metric_names_or_scalars = _MetricNamesOrScalars.from_perfometers(
                perfometer_.left,
                perfometer_.right,
            )
        case perfometer.Stacked():
            metric_names_or_scalars = _MetricNamesOrScalars.from_perfometers(
                perfometer_.lower,
                perfometer_.upper,
            )
    return _is_perfometer_applicable(translated_metrics, metric_names_or_scalars)


@dataclass(frozen=True)
class EvaluatedQuantity:
    title: LazyString | str
    unit: UnitInfo
    color: str
    value: int | float


def evaluate_quantity(
    quantity: (
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
    ),
    translated_metrics: Mapping[str, TranslatedMetric],
) -> EvaluatedQuantity:
    match quantity:
        case str():
            metric_ = translated_metrics[quantity]
            return EvaluatedQuantity(
                metric_["title"],
                metric_["unit"],
                metric_["color"],
                translated_metrics[quantity]["value"],
            )
        case metric.Constant():
            return EvaluatedQuantity(
                str(quantity.title),
                parse_unit(quantity.unit),
                parse_color(quantity.color),
                quantity.value,
            )
        case metric.WarningOf():
            metric_ = translated_metrics[quantity.name]
            return EvaluatedQuantity(
                _("Warning of ") + metric_["title"],
                metric_["unit"],
                "#ffff00",
                translated_metrics[quantity.name]["scalar"]["warn"],
            )
        case metric.CriticalOf():
            metric_ = translated_metrics[quantity.name]
            return EvaluatedQuantity(
                _("Critical of ") + metric_["title"],
                metric_["unit"],
                "#ff0000",
                translated_metrics[quantity.name]["scalar"]["crit"],
            )
        case metric.MinimumOf():
            metric_ = translated_metrics[quantity.name]
            return EvaluatedQuantity(
                _("Minimum of ") + metric_["title"],
                metric_["unit"],
                parse_color(quantity.color),
                translated_metrics[quantity.name]["scalar"]["min"],
            )
        case metric.MaximumOf():
            metric_ = translated_metrics[quantity.name]
            return EvaluatedQuantity(
                _("Maximum of ") + metric_["title"],
                metric_["unit"],
                parse_color(quantity.color),
                translated_metrics[quantity.name]["scalar"]["max"],
            )
        case metric.Sum():
            evaluated_first_summand = evaluate_quantity(quantity.summands[0], translated_metrics)
            return EvaluatedQuantity(
                str(quantity.title),
                evaluated_first_summand.unit,
                parse_color(quantity.color),
                (
                    evaluated_first_summand.value
                    + sum(
                        evaluate_quantity(s, translated_metrics).value
                        for s in quantity.summands[1:]
                    )
                ),
            )
        case metric.Product():
            product = 1.0
            for f in quantity.factors:
                product *= evaluate_quantity(f, translated_metrics).value
            return EvaluatedQuantity(
                str(quantity.title),
                parse_unit(quantity.unit),
                parse_color(quantity.color),
                product,
            )
        case metric.Difference():
            evaluated_minuend = evaluate_quantity(quantity.minuend, translated_metrics)
            evaluated_subtrahend = evaluate_quantity(quantity.subtrahend, translated_metrics)
            return EvaluatedQuantity(
                str(quantity.title),
                evaluated_minuend.unit,
                parse_color(quantity.color),
                evaluated_minuend.value - evaluated_subtrahend.value,
            )
        case metric.Fraction():
            return EvaluatedQuantity(
                str(quantity.title),
                parse_unit(quantity.unit),
                parse_color(quantity.color),
                (
                    evaluate_quantity(quantity.dividend, translated_metrics).value
                    / evaluate_quantity(quantity.divisor, translated_metrics).value
                ),
            )
