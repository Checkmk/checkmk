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

from ._color import mix_colors, parse_color, render_color, scalar_colors
from ._from_api import get_unit_info
from ._legacy import unit_info, UnitInfo
from ._translated_metrics import TranslatedMetric
from ._type_defs import GraphConsolidationFunction, LineType

# TODO CMK-15246 Checkmk 2.4: Remove legacy objects/RPNs


def _unit_mult(left_unit_info: UnitInfo, right_unit_info: UnitInfo) -> UnitInfo:
    # TODO: real unit computation!
    return (
        right_unit_info if left_unit_info in (unit_info[""], unit_info["count"]) else left_unit_info
    )


_unit_div: Callable[[UnitInfo, UnitInfo], UnitInfo] = _unit_mult
_unit_add: Callable[[UnitInfo, UnitInfo], UnitInfo] = _unit_mult
_unit_sub: Callable[[UnitInfo, UnitInfo], UnitInfo] = _unit_mult


def _choose_operator_color(a: str, b: str) -> str:
    if a == "#000000":
        return b
    if b == "#000000":
        return a
    return render_color(mix_colors(parse_color(a), parse_color(b)))


@dataclass(frozen=True)
class MetricExpressionResult:
    value: int | float
    unit_info: UnitInfo
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
            unit_info["count"] if isinstance(self.value, int) else unit_info[""],
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
            translated_metrics[self.name].unit_info,
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
            self.metric.evaluate(translated_metrics).unit_info,
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
            self.metric.evaluate(translated_metrics).unit_info,
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
            self.metric.evaluate(translated_metrics).unit_info,
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
            self.metric.evaluate(translated_metrics).unit_info,
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
            return MetricExpressionResult(0.0, unit_info[""], "#000000")

        first_result = self.summands[0].evaluate(translated_metrics)
        values = [first_result.value]
        unit_info_ = first_result.unit_info
        color = first_result.color
        for successor in self.summands[1:]:
            successor_result = successor.evaluate(translated_metrics)
            values.append(successor_result.value)
            unit_info_ = _unit_add(unit_info_, successor_result.unit_info)
            color = _choose_operator_color(color, successor_result.color)

        return MetricExpressionResult(sum(values), unit_info_, color)

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
            return MetricExpressionResult(1.0, unit_info[""], "#000000")

        first_result = self.factors[0].evaluate(translated_metrics)
        product = first_result.value
        unit_info_ = first_result.unit_info
        color = first_result.color
        for successor in self.factors[1:]:
            successor_result = successor.evaluate(translated_metrics)
            product *= successor_result.value
            unit_info_ = _unit_mult(unit_info_, successor_result.unit_info)
            color = _choose_operator_color(color, successor_result.color)

        return MetricExpressionResult(product, unit_info_, color)

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
            _unit_sub(minuend_result.unit_info, subtrahend_result.unit_info),
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
            _unit_div(dividend_result.unit_info, divisor_result.unit_info),
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
            return MetricExpressionResult(float("nan"), unit_info[""], "#000000")

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
            return MetricExpressionResult(float("nan"), unit_info[""], "#000000")

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
            unit_info["%"],
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
            return MetricExpressionResult(float("nan"), unit_info[""], "#000000")

        result = Sum(self.operands).evaluate(translated_metrics)
        return MetricExpressionResult(
            result.value / len(self.operands),
            result.unit_info,
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
        return MetricExpressionResult(float("nan"), unit_info[""], "#000000")

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


def _extract_consolidation(
    expression: str,
) -> tuple[str, GraphConsolidationFunction | None]:
    if expression.endswith(".max"):
        return expression[:-4], "max"
    if expression.endswith(".min"):
        return expression[:-4], "min"
    if expression.endswith(".average"):
        return expression[:-8], "average"
    return expression, None


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

    var_name, consolidation = _extract_consolidation(raw_expression)
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


def _parse_expression(
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


def parse_base_expression(
    raw_expression: str | int | float,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> BaseMetricExpression:
    if isinstance(raw_expression, (int, float)):
        return Constant(raw_expression)
    (
        stack,
        _unit_id,
        _color,
    ) = _parse_expression(raw_expression, translated_metrics)
    if isinstance(resolved := _resolve_stack(stack), BaseMetricExpression):
        return resolved
    raise TypeError(resolved)


@dataclass(frozen=True)
class MetricExpression:
    base: BaseMetricExpression
    _: KW_ONLY
    line_type: LineType
    title: str = ""
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = self.base.evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.base.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from self.base.scalar_names()


def parse_expression(
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
            unit_id="",
            color="",
        )
    (
        stack,
        unit_id,
        color,
    ) = _parse_expression(raw_expression, translated_metrics)
    if isinstance(resolved := _resolve_stack(stack), BaseMetricExpression):
        return MetricExpression(
            resolved,
            line_type=line_type,
            title=title,
            unit_id=unit_id,
            color=color,
        )
    raise TypeError(resolved)


def parse_conditional_expression(
    raw_expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> ConditionalMetricExpression:
    (
        stack,
        _unit_id,
        _color,
    ) = _parse_expression(raw_expression, translated_metrics)
    if isinstance(resolved := _resolve_stack(stack), ConditionalMetricExpression):
        return resolved
    raise TypeError(resolved)
