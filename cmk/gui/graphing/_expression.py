#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import contextlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, KW_ONLY
from typing import Literal

from cmk.utils.metrics import MetricName

from cmk.gui.i18n import _, translate_to_current_language

from cmk.graphing.v1 import metrics as metrics_api

from ._color import mix_colors, parse_color, parse_color_from_api, render_color, scalar_colors
from ._formatter import AutoPrecision, StrictPrecision
from ._from_api import parse_unit_from_api
from ._legacy import get_unit_info, unit_info, UnitInfo
from ._metrics import get_metric_spec
from ._translated_metrics import TranslatedMetric
from ._type_defs import GraphConsolidationFunction, LineType
from ._unit import ConvertibleUnitSpecification, DecimalNotation

# TODO CMK-15246 Checkmk 2.4: Remove legacy objects/RPNs

_FALLBACK_UNIT_SPEC_FLOAT = ConvertibleUnitSpecification(
    notation=DecimalNotation(symbol=""),
    precision=AutoPrecision(digits=2),
)
_FALLBACK_UNIT_SPEC_INT = ConvertibleUnitSpecification(
    notation=DecimalNotation(symbol=""),
    precision=StrictPrecision(digits=2),
)


def _unit_mult(
    left_unit_spec: UnitInfo | ConvertibleUnitSpecification,
    right_unit_spec: UnitInfo | ConvertibleUnitSpecification,
) -> UnitInfo | ConvertibleUnitSpecification:
    # TODO: real unit computation!
    if isinstance(left_unit_spec, UnitInfo) and left_unit_spec in (
        unit_info[""],
        unit_info["count"],
    ):
        return right_unit_spec
    if (
        isinstance(left_unit_spec, ConvertibleUnitSpecification)
        and not left_unit_spec.notation.symbol
    ):
        return right_unit_spec
    return left_unit_spec


_unit_div: Callable[
    [
        UnitInfo | ConvertibleUnitSpecification,
        UnitInfo | ConvertibleUnitSpecification,
    ],
    UnitInfo | ConvertibleUnitSpecification,
] = _unit_mult
_unit_add: Callable[
    [
        UnitInfo | ConvertibleUnitSpecification,
        UnitInfo | ConvertibleUnitSpecification,
    ],
    UnitInfo | ConvertibleUnitSpecification,
] = _unit_mult
_unit_sub: Callable[
    [
        UnitInfo | ConvertibleUnitSpecification,
        UnitInfo | ConvertibleUnitSpecification,
    ],
    UnitInfo | ConvertibleUnitSpecification,
] = _unit_mult


def _choose_operator_color(a: str, b: str) -> str:
    if a == "#000000":
        return b
    if b == "#000000":
        return a
    return render_color(mix_colors(parse_color(a), parse_color(b)))


@dataclass(frozen=True)
class MetricExpressionResult:
    value: int | float
    unit_spec: ConvertibleUnitSpecification | UnitInfo
    color: str


@dataclass(frozen=True)
class ScalarName:
    metric_name: str
    scalar_name: Literal["warn", "crit", "min", "max"]


class BaseMetricExpression(abc.ABC):
    @abc.abstractmethod
    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        raise NotImplementedError()

    @abc.abstractmethod
    def metric_names(self) -> Iterator[str]:
        raise NotImplementedError()

    @abc.abstractmethod
    def scalar_names(self) -> Iterator[ScalarName]:
        raise NotImplementedError()


@dataclass(frozen=True)
class Constant(BaseMetricExpression):
    value: int | float

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            self.value,
            _FALLBACK_UNIT_SPEC_INT if isinstance(self.value, int) else _FALLBACK_UNIT_SPEC_FLOAT,
            "#000000",
        )

    def metric_names(self) -> Iterator[str]:
        yield from ()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from ()


@dataclass(frozen=True)
class Metric(BaseMetricExpression):
    name: MetricName
    consolidation: GraphConsolidationFunction | None = None

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.name].value,
            translated_metrics[self.name].unit_spec,
            translated_metrics[self.name].color,
        )

    def metric_names(self) -> Iterator[str]:
        yield self.name

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from ()


@dataclass(frozen=True)
class WarningOf(BaseMetricExpression):
    metric: Metric

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name].scalar["warn"],
            self.metric.evaluate(translated_metrics).unit_spec,
            scalar_colors.get("warn", "#808080"),
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.metric.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield ScalarName(self.metric.name, "warn")


@dataclass(frozen=True)
class CriticalOf(BaseMetricExpression):
    metric: Metric

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name].scalar["crit"],
            self.metric.evaluate(translated_metrics).unit_spec,
            scalar_colors.get("crit", "#808080"),
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.metric.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield ScalarName(self.metric.name, "crit")


@dataclass(frozen=True)
class MinimumOf(BaseMetricExpression):
    metric: Metric

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name].scalar["min"],
            self.metric.evaluate(translated_metrics).unit_spec,
            scalar_colors.get("min", "#808080"),
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.metric.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield ScalarName(self.metric.name, "min")


@dataclass(frozen=True)
class MaximumOf(BaseMetricExpression):
    metric: Metric

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name].scalar["max"],
            self.metric.evaluate(translated_metrics).unit_spec,
            scalar_colors.get("max", "#808080"),
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.metric.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield ScalarName(self.metric.name, "max")


@dataclass(frozen=True)
class Sum(BaseMetricExpression):
    summands: Sequence[BaseMetricExpression]

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.summands) == 0:
            return MetricExpressionResult(0.0, _FALLBACK_UNIT_SPEC_FLOAT, "#000000")

        first_result = self.summands[0].evaluate(translated_metrics)
        values = [first_result.value]
        unit_spec = first_result.unit_spec
        color = first_result.color
        for successor in self.summands[1:]:
            successor_result = successor.evaluate(translated_metrics)
            values.append(successor_result.value)
            unit_spec = _unit_add(unit_spec, successor_result.unit_spec)
            color = _choose_operator_color(color, successor_result.color)

        return MetricExpressionResult(sum(values), unit_spec, color)

    def metric_names(self) -> Iterator[str]:
        yield from (n for s in self.summands for n in s.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for s in self.summands for n in s.scalar_names())


@dataclass(frozen=True)
class Product(BaseMetricExpression):
    factors: Sequence[BaseMetricExpression]

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.factors) == 0:
            return MetricExpressionResult(1.0, _FALLBACK_UNIT_SPEC_FLOAT, "#000000")

        first_result = self.factors[0].evaluate(translated_metrics)
        product = first_result.value
        unit_spec = first_result.unit_spec
        color = first_result.color
        for successor in self.factors[1:]:
            successor_result = successor.evaluate(translated_metrics)
            product *= successor_result.value
            unit_spec = _unit_mult(unit_spec, successor_result.unit_spec)
            color = _choose_operator_color(color, successor_result.color)

        return MetricExpressionResult(product, unit_spec, color)

    def metric_names(self) -> Iterator[str]:
        yield from (n for f in self.factors for n in f.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for f in self.factors for n in f.scalar_names())


@dataclass(frozen=True, kw_only=True)
class Difference(BaseMetricExpression):
    minuend: BaseMetricExpression
    subtrahend: BaseMetricExpression

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        minuend_result = self.minuend.evaluate(translated_metrics)
        subtrahend_result = self.subtrahend.evaluate(translated_metrics)

        if (subtrahend_result.value) == 0.0:
            value = 0.0
        else:
            value = minuend_result.value - subtrahend_result.value

        return MetricExpressionResult(
            value,
            _unit_sub(minuend_result.unit_spec, subtrahend_result.unit_spec),
            _choose_operator_color(minuend_result.color, subtrahend_result.color),
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.minuend.metric_names()
        yield from self.subtrahend.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from self.minuend.scalar_names()
        yield from self.subtrahend.scalar_names()


@dataclass(frozen=True, kw_only=True)
class Fraction(BaseMetricExpression):
    dividend: BaseMetricExpression
    divisor: BaseMetricExpression

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        dividend_result = self.dividend.evaluate(translated_metrics)
        divisor_result = self.divisor.evaluate(translated_metrics)

        if (divisor_result.value) == 0.0:
            value = 0.0
        else:
            value = dividend_result.value / divisor_result.value

        return MetricExpressionResult(
            value,
            _unit_div(dividend_result.unit_spec, divisor_result.unit_spec),
            _choose_operator_color(dividend_result.color, divisor_result.color),
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.dividend.metric_names()
        yield from self.divisor.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from self.dividend.scalar_names()
        yield from self.divisor.scalar_names()


@dataclass(frozen=True)
class Minimum(BaseMetricExpression):
    operands: Sequence[BaseMetricExpression]

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(float("nan"), _FALLBACK_UNIT_SPEC_FLOAT, "#000000")

        minimum = self.operands[0].evaluate(translated_metrics)
        for operand in self.operands[1:]:
            operand_result = operand.evaluate(translated_metrics)
            if operand_result.value < minimum.value:
                minimum = operand_result

        return minimum

    def metric_names(self) -> Iterator[str]:
        yield from (n for o in self.operands for n in o.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for o in self.operands for n in o.scalar_names())


@dataclass(frozen=True)
class Maximum(BaseMetricExpression):
    operands: Sequence[BaseMetricExpression]

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(float("nan"), _FALLBACK_UNIT_SPEC_FLOAT, "#000000")

        maximum = self.operands[0].evaluate(translated_metrics)
        for operand in self.operands[1:]:
            operand_result = operand.evaluate(translated_metrics)
            if operand_result.value > maximum.value:
                maximum = operand_result

        return maximum

    def metric_names(self) -> Iterator[str]:
        yield from (n for o in self.operands for n in o.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for o in self.operands for n in o.scalar_names())


# Composed metric declarations:


@dataclass(frozen=True, kw_only=True)
class Percent(BaseMetricExpression):
    """percentage = 100 * percent_value / base_value"""

    percent_value: BaseMetricExpression
    base_value: BaseMetricExpression

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            (
                Fraction(
                    dividend=Product([Constant(100.0), self.percent_value]),
                    divisor=self.base_value,
                )
                .evaluate(translated_metrics)
                .value
            ),
            ConvertibleUnitSpecification(
                notation=DecimalNotation(symbol="%"),
                precision=AutoPrecision(digits=2),
            ),
            self.percent_value.evaluate(translated_metrics).color,
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.percent_value.metric_names()
        yield from self.base_value.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from self.percent_value.scalar_names()
        yield from self.base_value.scalar_names()


# Special metric declarations for custom graphs


@dataclass(frozen=True)
class Average(BaseMetricExpression):
    operands: Sequence[BaseMetricExpression]

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(float("nan"), _FALLBACK_UNIT_SPEC_FLOAT, "#000000")

        result = Sum(self.operands).evaluate(translated_metrics)
        return MetricExpressionResult(
            result.value / len(self.operands),
            result.unit_spec,
            result.color,
        )

    def metric_names(self) -> Iterator[str]:
        yield from (n for o in self.operands for n in o.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for o in self.operands for n in o.scalar_names())


@dataclass(frozen=True)
class Merge(BaseMetricExpression):
    operands: Sequence[BaseMetricExpression]

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        # TODO None?
        for operand in self.operands:
            if (result := operand.evaluate(translated_metrics)).value is not None:
                return result
        return MetricExpressionResult(float("nan"), _FALLBACK_UNIT_SPEC_FLOAT, "#000000")

    def metric_names(self) -> Iterator[str]:
        yield from (n for o in self.operands for n in o.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for o in self.operands for n in o.scalar_names())


class ConditionalMetricExpression(abc.ABC):
    @abc.abstractmethod
    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> bool:
        raise NotImplementedError()


@dataclass(frozen=True, kw_only=True)
class GreaterThan(ConditionalMetricExpression):
    left: BaseMetricExpression
    right: BaseMetricExpression

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> bool:
        return (
            self.left.evaluate(translated_metrics).value
            > self.right.evaluate(translated_metrics).value
        )


@dataclass(frozen=True, kw_only=True)
class GreaterEqualThan(ConditionalMetricExpression):
    left: BaseMetricExpression
    right: BaseMetricExpression

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> bool:
        return (
            self.left.evaluate(translated_metrics).value
            >= self.right.evaluate(translated_metrics).value
        )


@dataclass(frozen=True, kw_only=True)
class LessThan(ConditionalMetricExpression):
    left: BaseMetricExpression
    right: BaseMetricExpression

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> bool:
        return (
            self.left.evaluate(translated_metrics).value
            < self.right.evaluate(translated_metrics).value
        )


@dataclass(frozen=True, kw_only=True)
class LessEqualThan(ConditionalMetricExpression):
    left: BaseMetricExpression
    right: BaseMetricExpression

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> bool:
        return (
            self.left.evaluate(translated_metrics).value
            <= self.right.evaluate(translated_metrics).value
        )


def _extract_consolidation_function(
    raw_expression: str,
) -> tuple[str, GraphConsolidationFunction | None]:
    if raw_expression.endswith(".max"):
        return raw_expression[:-4], "max"
    if raw_expression.endswith(".min"):
        return raw_expression[:-4], "min"
    if raw_expression.endswith(".average"):
        return raw_expression[:-8], "average"
    return raw_expression, None


def _from_scalar(
    scalar_name: str, metric: Metric
) -> WarningOf | CriticalOf | MinimumOf | MaximumOf:
    match scalar_name:
        case "warn":
            return WarningOf(metric)
        case "crit":
            return CriticalOf(metric)
        case "min":
            return MinimumOf(metric)
        case "max":
            return MaximumOf(metric)
    raise ValueError(scalar_name)


def _parse_single_expression(
    raw_expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> BaseMetricExpression:
    if raw_expression not in translated_metrics:
        with contextlib.suppress(ValueError):
            return Constant(int(raw_expression))
        with contextlib.suppress(ValueError):
            return Constant(float(raw_expression))

    var_name, consolidation = _extract_consolidation_function(raw_expression)
    if percent := var_name.endswith("(%)"):
        var_name = var_name[:-3]

    if ":" in var_name:
        var_name, scalar_name = var_name.split(":")
        metric = Metric(var_name, consolidation=consolidation)
        scalar = _from_scalar(scalar_name, metric)
        return Percent(percent_value=scalar, base_value=MaximumOf(metric)) if percent else scalar

    metric = Metric(var_name, consolidation=consolidation)
    return Percent(percent_value=metric, base_value=MaximumOf(metric)) if percent else metric


_RPNOperators = Literal["+", "*", "-", "/", "MIN", "MAX", "AVERAGE", "MERGE", ">", ">=", "<", "<="]


def _parse_legacy_expression(
    raw_expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> tuple[Sequence[BaseMetricExpression | _RPNOperators], str, str]:
    # Evaluates an expression, returns a triple of value, unit and color.
    # e.g. "fs_used:max"    -> 12.455, "b", "#00ffc6",
    # e.g. "fs_used(%)"     -> 17.5,   "%", "#00ffc6",
    # e.g. "fs_used:max(%)" -> 100.0,  "%", "#00ffc6",
    # e.g. 123.4            -> 123.4,  "",  "#000000"
    # e.g. "123.4#ff0000"   -> 123.4,  "",  "#ff0000",
    # Note:
    # "fs_growth.max" is the same as fs_growth. The .max is just
    # relevant when fetching RRD data and is used for selecting
    # the consolidation function MAX.

    color = ""
    if "#" in raw_expression:
        # drop appended color information
        raw_expression, color_ = raw_expression.rsplit("#", 1)
        color = f"#{color_}"

    unit_id = ""
    if "@" in raw_expression:
        # appended unit name
        raw_expression, unit_id = raw_expression.rsplit("@", 1)

    stack: list[BaseMetricExpression | _RPNOperators] = []
    for p in raw_expression.split(","):
        match p:
            case "+":
                stack.append("+")
            case "-":
                stack.append("-")
            case "*":
                stack.append("*")
            case "/":
                stack.append("/")
            case "MIN":
                stack.append("MIN")
            case "MAX":
                stack.append("MAX")
            case "AVERAGE":
                stack.append("AVERAGE")
            case "MERGE":
                stack.append("MERGE")
            case ">":
                stack.append(">")
            case ">=":
                stack.append(">=")
            case "<":
                stack.append("<")
            case "<=":
                stack.append("<=")
            case _:
                stack.append(_parse_single_expression(p, translated_metrics))

    return stack, unit_id, color


def _resolve_stack(
    stack: Sequence[BaseMetricExpression | _RPNOperators],
) -> BaseMetricExpression | ConditionalMetricExpression:
    resolved: list[BaseMetricExpression | ConditionalMetricExpression] = []
    for element in stack:
        if isinstance(element, BaseMetricExpression):
            resolved.append(element)
            continue

        if not isinstance(right := resolved.pop(), BaseMetricExpression):
            raise TypeError(right)

        if not isinstance(left := resolved.pop(), BaseMetricExpression):
            raise TypeError(left)

        match element:
            case "+":
                resolved.append(Sum([left, right]))
            case "-":
                resolved.append(Difference(minuend=left, subtrahend=right))
            case "*":
                resolved.append(Product([left, right]))
            case "/":
                # Handle zero division by always adding a tiny bit to the divisor
                resolved.append(Fraction(dividend=left, divisor=Sum([right, Constant(1e-16)])))
            case "MIN":
                resolved.append(Minimum([left, right]))
            case "MAX":
                resolved.append(Maximum([left, right]))
            case "AVERAGE":
                resolved.append(Average([left, right]))
            case "MERGE":
                resolved.append(Merge([left, right]))
            case ">=":
                resolved.append(GreaterEqualThan(left=left, right=right))
            case ">":
                resolved.append(GreaterThan(left=left, right=right))
            case "<=":
                resolved.append(LessEqualThan(left=left, right=right))
            case "<":
                resolved.append(LessThan(left=left, right=right))

    return resolved[0]


def parse_legacy_base_expression(
    raw_expression: str | int | float,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> BaseMetricExpression:
    if isinstance(raw_expression, (int, float)):
        return Constant(raw_expression)
    (
        stack,
        _unit_id,
        _color,
    ) = _parse_legacy_expression(raw_expression, translated_metrics)
    if isinstance(resolved := _resolve_stack(stack), BaseMetricExpression):
        return resolved
    raise TypeError(resolved)


@dataclass(frozen=True)
class MetricExpression:
    base: BaseMetricExpression
    _: KW_ONLY
    line_type: LineType
    title: str = ""
    unit_spec: ConvertibleUnitSpecification | None | str = None
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = self.base.evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            (
                get_unit_info(self.unit_spec)
                if isinstance(self.unit_spec, str)
                else (self.unit_spec or evaluated.unit_spec)
            ),
            self.color or evaluated.color,
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.base.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from self.base.scalar_names()


def parse_legacy_expression(
    raw_expression: str | int | float,
    line_type: LineType,
    title: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> MetricExpression:
    if isinstance(raw_expression, (int, float)):
        return MetricExpression(
            Constant(raw_expression),
            line_type=line_type,
            title=title,
            unit_spec=None,
            color="",
        )
    (
        stack,
        unit_id,
        color,
    ) = _parse_legacy_expression(raw_expression, translated_metrics)
    if isinstance(resolved := _resolve_stack(stack), BaseMetricExpression):
        return MetricExpression(
            resolved,
            line_type=line_type,
            title=title,
            unit_spec=unit_id or None,
            color=color,
        )
    raise TypeError(resolved)


def parse_legacy_conditional_expression(
    raw_expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> ConditionalMetricExpression:
    (
        stack,
        _unit_id,
        _color,
    ) = _parse_legacy_expression(raw_expression, translated_metrics)
    if isinstance(resolved := _resolve_stack(stack), ConditionalMetricExpression):
        return resolved
    raise TypeError(resolved)


def parse_base_expression_from_api(
    quantity: (
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
    ),
) -> BaseMetricExpression:
    match quantity:
        case str():
            return Metric(quantity)
        case metrics_api.Constant():
            return Constant(quantity.value)
        case metrics_api.WarningOf():
            return WarningOf(Metric(quantity.metric_name))
        case metrics_api.CriticalOf():
            return CriticalOf(Metric(quantity.metric_name))
        case metrics_api.MinimumOf():
            return MinimumOf(Metric(quantity.metric_name))
        case metrics_api.MaximumOf():
            return MaximumOf(Metric(quantity.metric_name))
        case metrics_api.Sum():
            return Sum([parse_base_expression_from_api(s) for s in quantity.summands])
        case metrics_api.Product():
            return Product([parse_base_expression_from_api(f) for f in quantity.factors])
        case metrics_api.Difference():
            return Difference(
                minuend=parse_base_expression_from_api(quantity.minuend),
                subtrahend=parse_base_expression_from_api(quantity.subtrahend),
            )
        case metrics_api.Fraction():
            return Fraction(
                dividend=parse_base_expression_from_api(quantity.dividend),
                divisor=parse_base_expression_from_api(quantity.divisor),
            )


def parse_expression_from_api(
    quantity: (
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
    ),
    line_type: Literal["line", "-line", "stack", "-stack"],
) -> MetricExpression:
    match quantity:
        case str():
            return MetricExpression(
                Metric(quantity),
                line_type=line_type,
                title=get_metric_spec(quantity).title,
            )
        case metrics_api.Constant():
            return MetricExpression(
                Constant(quantity.value),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
                unit_spec=parse_unit_from_api(quantity.unit),
                color=parse_color_from_api(quantity.color),
            )
        case metrics_api.WarningOf():
            return MetricExpression(
                WarningOf(Metric(quantity.metric_name)),
                line_type=line_type,
                title=_("Warning of %s") % get_metric_spec(quantity.metric_name).title,
            )
        case metrics_api.CriticalOf():
            return MetricExpression(
                CriticalOf(Metric(quantity.metric_name)),
                line_type=line_type,
                title=_("Critical of %s") % get_metric_spec(quantity.metric_name).title,
            )
        case metrics_api.MinimumOf():
            return MetricExpression(
                MinimumOf(Metric(quantity.metric_name)),
                line_type=line_type,
                title=get_metric_spec(quantity.metric_name).title,
                color=parse_color_from_api(quantity.color),
            )
        case metrics_api.MaximumOf():
            return MetricExpression(
                MaximumOf(Metric(quantity.metric_name)),
                line_type=line_type,
                title=get_metric_spec(quantity.metric_name).title,
                color=parse_color_from_api(quantity.color),
            )
        case metrics_api.Sum():
            return MetricExpression(
                Sum([parse_base_expression_from_api(s) for s in quantity.summands]),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
                color=parse_color_from_api(quantity.color),
            )
        case metrics_api.Product():
            return MetricExpression(
                Product([parse_base_expression_from_api(f) for f in quantity.factors]),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
                unit_spec=parse_unit_from_api(quantity.unit),
                color=parse_color_from_api(quantity.color),
            )
        case metrics_api.Difference():
            return MetricExpression(
                Difference(
                    minuend=parse_base_expression_from_api(quantity.minuend),
                    subtrahend=parse_base_expression_from_api(quantity.subtrahend),
                ),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
                color=parse_color_from_api(quantity.color),
            )
        case metrics_api.Fraction():
            return MetricExpression(
                Fraction(
                    dividend=parse_base_expression_from_api(quantity.dividend),
                    divisor=parse_base_expression_from_api(quantity.divisor),
                ),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
                unit_spec=parse_unit_from_api(quantity.unit),
                color=parse_color_from_api(quantity.color),
            )
