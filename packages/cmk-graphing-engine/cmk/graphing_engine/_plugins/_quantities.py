#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping
from typing import assert_never

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable
from cmk.graphing_engine._data._fetched import ScalarKind
from cmk.graphing_engine._data._units import CurveAttributes
from cmk.graphing_engine._quantities._expressions import (
    Constant,
    Difference,
    Fraction,
    Product,
    Sum,
)
from cmk.graphing_engine._quantities._quantity import QuantityProtocol
from cmk.graphing_engine._rrd._metrics import rrd_metric_of, ScalarOf
from cmk.graphing_engine._rrd._naming import Service

from ._display import metric_display_attributes, parse_color, parse_unit, scalar_attributes
from ._types import ApiQuantity, ApiScalar, operands_of


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


def attributes_of_quantity(
    quantity: ApiQuantity,
    localizer: Callable[[str], str],
    registered_metrics: Mapping[str, metrics_v1.Metric],
) -> CurveAttributes:
    match quantity:
        case str():
            return metric_display_attributes(quantity, localizer, registered_metrics)
        case metrics_v1.Constant():
            return CurveAttributes(
                title=quantity.title.localize(localizer),
                unit=parse_unit(quantity.unit),
                color=parse_color(quantity.color),
            )
        case (
            metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
        ):
            return scalar_attributes(
                attributes_of_quantity(quantity.metric_name, localizer, registered_metrics),
                scalar_kind_of(quantity),
                localizer,
            )
        case metrics_v1.MinimumOf() | metrics_v1.MaximumOf():
            extremum = scalar_attributes(
                attributes_of_quantity(quantity.metric_name, localizer, registered_metrics),
                scalar_kind_of(quantity),
                localizer,
            )
            return CurveAttributes(
                title=extremum.title, unit=extremum.unit, color=parse_color(quantity.color)
            )
        case metrics_v1.Sum() | metrics_v1.Difference():
            # A sum and a difference are in the unit of what they add up or take apart, so the API
            # does not spell one out: it is the first operand's.
            return CurveAttributes(
                title=quantity.title.localize(localizer),
                unit=attributes_of_quantity(
                    operands_of(quantity)[0], localizer, registered_metrics
                ).unit,
                color=parse_color(quantity.color),
            )
        case metrics_v1.Product() | metrics_v1.Fraction():
            return CurveAttributes(
                title=quantity.title.localize(localizer),
                unit=parse_unit(quantity.unit),
                color=parse_color(quantity.color),
            )
        case _:
            assert_never(quantity)


def parse_quantity(quantity: ApiQuantity, service: Service) -> QuantityProtocol:
    match quantity:
        case str():
            return rrd_metric_of(service, quantity)
        case metrics_v1.Constant():
            return Constant(quantity.value)
        case (
            metrics_v2_unstable.LowerWarningOf()
            | metrics_v2_unstable.LowerCriticalOf()
            | metrics_v1.WarningOf()
            | metrics_v1.CriticalOf()
            | metrics_v1.MinimumOf()
            | metrics_v1.MaximumOf()
        ):
            return ScalarOf(
                metric=rrd_metric_of(service, quantity.metric_name),
                scalar_kind=scalar_kind_of(quantity),
            )
        case metrics_v1.Sum():
            return Sum(
                summands=tuple(parse_quantity(s, service) for s in quantity.summands),
            )
        case metrics_v1.Product():
            return Product(
                factors=tuple(parse_quantity(f, service) for f in quantity.factors),
            )
        case metrics_v1.Difference():
            return Difference(
                minuend=parse_quantity(quantity.minuend, service),
                subtrahend=parse_quantity(quantity.subtrahend, service),
            )
        case metrics_v1.Fraction():
            return Fraction(
                dividend=parse_quantity(quantity.dividend, service),
                divisor=parse_quantity(quantity.divisor, service),
            )
        case _:
            assert_never(quantity)
