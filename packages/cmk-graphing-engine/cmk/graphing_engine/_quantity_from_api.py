#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The quantity layer of the plug-in API: turning an API quantity into the engine quantity that
# evaluates it, and dressing that quantity for drawing. Shared by everything a plug-in describes -
# a graph's curves and a perfometer's segments alike.

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import assert_never

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable

from ._api_plugins import ApiQuantity, ApiScalar, operands_of
from ._display import (
    FALLBACK_ATTRIBUTES,
    metric_display_attributes,
    parse_color,
    parse_unit,
)
from ._naming import Service
from ._quantities import (
    Constant,
    Difference,
    Fraction,
    Product,
    rrd_metric_of,
    RRDMetric,
    ScalarKind,
    ScalarOf,
    Sum,
)
from ._quantity import Curve, QuantityProtocol
from ._units import CurveAttributes


def scalar_kind_of(scalar: ApiScalar) -> ScalarKind:
    match scalar:
        case metrics_v1.WarningOf():
            return ScalarKind.WARNING
        case metrics_v1.CriticalOf():
            return ScalarKind.CRITICAL
        case metrics_v2_unstable.LowerWarningOf():
            return ScalarKind.LOWER_WARNING
        case metrics_v2_unstable.LowerCriticalOf():
            return ScalarKind.LOWER_CRITICAL
        case metrics_v1.MinimumOf():
            return ScalarKind.MINIMUM
        case metrics_v1.MaximumOf():
            return ScalarKind.MAXIMUM
        case _:
            assert_never(scalar)


@dataclass(frozen=True)
class QuantityContext:
    """What a quantity is parsed for: the service it is read from, and how to name it."""

    service: Service
    localizer: Callable[[str], str]
    registered_metrics: Mapping[str, metrics_v1.Metric]

    def metric(self, metric_name: str) -> RRDMetric:
        return rrd_metric_of(self.service, metric_name)


def _curve_display(quantity: ApiQuantity, context: QuantityContext) -> CurveAttributes:
    match quantity:
        case str():
            return metric_display_attributes(
                quantity, context.localizer, context.registered_metrics
            )
        case metrics_v1.Constant():
            return CurveAttributes(
                title=quantity.title.localize(context.localizer),
                unit=parse_unit(quantity.unit),
                color=parse_color(quantity.color),
            )
        case (
            metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
        ):
            return _curve_display(quantity.metric_name, context)
        case metrics_v1.MinimumOf() | metrics_v1.MaximumOf():
            attributes = _curve_display(quantity.metric_name, context)
            return CurveAttributes(
                title=attributes.title, unit=attributes.unit, color=parse_color(quantity.color)
            )
        case metrics_v1.Sum() | metrics_v1.Difference():
            # A sum and a difference are in the unit of what they add up or take apart, so the API
            # does not spell one out: it is the first operand's.
            return CurveAttributes(
                title=quantity.title.localize(context.localizer),
                unit=_curve_display(operands_of(quantity)[0], context).unit,
                color=parse_color(quantity.color),
            )
        case metrics_v1.Product() | metrics_v1.Fraction():
            return CurveAttributes(
                title=quantity.title.localize(context.localizer),
                unit=parse_unit(quantity.unit),
                color=parse_color(quantity.color),
            )
        case _:
            assert_never(quantity)


def parse_quantity(quantity: ApiQuantity, context: QuantityContext) -> QuantityProtocol:
    match quantity:
        case str():
            return context.metric(quantity)
        case metrics_v1.Constant():
            return Constant(quantity.value, display=_curve_display(quantity, context))
        case (
            metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
        ):
            return ScalarOf(
                metric=context.metric(quantity.metric_name),
                scalar_kind=scalar_kind_of(quantity),
            )
        case metrics_v1.MinimumOf() | metrics_v1.MaximumOf():
            return ScalarOf(
                metric=context.metric(quantity.metric_name),
                scalar_kind=scalar_kind_of(quantity),
                color=parse_color(quantity.color),
            )
        case metrics_v1.Sum():
            return Sum(
                summands=[parse_quantity(s, context) for s in quantity.summands],
                display=_curve_display(quantity, context),
            )
        case metrics_v1.Product():
            return Product(
                factors=[parse_quantity(f, context) for f in quantity.factors],
                display=_curve_display(quantity, context),
            )
        case metrics_v1.Difference():
            return Difference(
                minuend=parse_quantity(quantity.minuend, context),
                subtrahend=parse_quantity(quantity.subtrahend, context),
                display=_curve_display(quantity, context),
            )
        case metrics_v1.Fraction():
            return Fraction(
                dividend=parse_quantity(quantity.dividend, context),
                divisor=parse_quantity(quantity.divisor, context),
                display=_curve_display(quantity, context),
            )
        case _:
            assert_never(quantity)


def build_curve(
    quantity: QuantityProtocol,
    localizer: Callable[[str], str],
    registered_metrics: Mapping[str, metrics_v1.Metric],
) -> Curve:
    return Curve(
        quantity=quantity,
        attributes=quantity.attributes(localizer, registered_metrics) or FALLBACK_ATTRIBUTES,
    )
