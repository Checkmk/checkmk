#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import contextlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from cmk.utils.metrics import MetricName

from ._color import mix_colors, parse_color, render_color, scalar_colors
from ._from_api import get_unit_info
from ._legacy import unit_info, UnitInfo
from ._translated_metrics import TranslatedMetric
from ._type_defs import GraphConsolidationFunction

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


class MetricExpression(abc.ABC):
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
class _Constant(MetricExpression):
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


@dataclass(frozen=True, kw_only=True)
class Constant(_Constant):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


@dataclass(frozen=True)
class _Metric(MetricExpression):
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
class Metric(_Metric):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


@dataclass(frozen=True)
class _WarningOf(MetricExpression):
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


@dataclass(frozen=True, kw_only=True)
class WarningOf(_WarningOf):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


@dataclass(frozen=True)
class _CriticalOf(MetricExpression):
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


@dataclass(frozen=True, kw_only=True)
class CriticalOf(_CriticalOf):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


@dataclass(frozen=True)
class _MinimumOf(MetricExpression):
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


@dataclass(frozen=True, kw_only=True)
class MinimumOf(_MinimumOf):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


@dataclass(frozen=True)
class _MaximumOf(MetricExpression):
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


@dataclass(frozen=True, kw_only=True)
class MaximumOf(_MaximumOf):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


@dataclass(frozen=True)
class _Sum(MetricExpression):
    summands: Sequence[MetricExpression]

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


@dataclass(frozen=True, kw_only=True)
class Sum(_Sum):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


@dataclass(frozen=True)
class _Product(MetricExpression):
    factors: Sequence[MetricExpression]

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
class Product(_Product):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


@dataclass(frozen=True, kw_only=True)
class _Difference(MetricExpression):
    minuend: MetricExpression
    subtrahend: MetricExpression

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
class Difference(_Difference):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


@dataclass(frozen=True, kw_only=True)
class _Fraction(MetricExpression):
    dividend: MetricExpression
    divisor: MetricExpression

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


@dataclass(frozen=True, kw_only=True)
class Fraction(_Fraction):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


@dataclass(frozen=True)
class _Minimum(MetricExpression):
    operands: Sequence[MetricExpression]

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


@dataclass(frozen=True, kw_only=True)
class Minimum(_Minimum):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


@dataclass(frozen=True)
class _Maximum(MetricExpression):
    operands: Sequence[MetricExpression]

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


@dataclass(frozen=True, kw_only=True)
class Maximum(_Maximum):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


# Composed metric declarations:


@dataclass(frozen=True, kw_only=True)
class _Percent(MetricExpression):
    """percentage = 100 * percent_value / base_value"""

    percent_value: MetricExpression
    base_value: MetricExpression

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


@dataclass(frozen=True, kw_only=True)
class Percent(_Percent):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


# Special metric declarations for custom graphs


@dataclass(frozen=True)
class _Average(MetricExpression):
    operands: Sequence[MetricExpression]

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


@dataclass(frozen=True, kw_only=True)
class Average(_Average):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


@dataclass(frozen=True)
class _Merge(MetricExpression):
    operands: Sequence[MetricExpression]

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


@dataclass(frozen=True, kw_only=True)
class Merge(_Merge):
    unit_id: str = ""
    color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        evaluated = super().evaluate(translated_metrics)
        return MetricExpressionResult(
            evaluated.value,
            get_unit_info(self.unit_id) if self.unit_id else evaluated.unit_info,
            self.color or evaluated.color,
        )


class ConditionalMetricExpression(abc.ABC):
    @abc.abstractmethod
    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> bool:
        raise NotImplementedError()


@dataclass(frozen=True, kw_only=True)
class GreaterThan(ConditionalMetricExpression):
    left: MetricExpression
    right: MetricExpression

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
    left: MetricExpression
    right: MetricExpression

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
    left: MetricExpression
    right: MetricExpression

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
    left: MetricExpression
    right: MetricExpression

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
) -> _WarningOf | _CriticalOf | _MinimumOf | _MaximumOf:
    match scalar_name:
        case "warn":
            return _WarningOf(metric)
        case "crit":
            return _CriticalOf(metric)
        case "min":
            return _MinimumOf(metric)
        case "max":
            return _MaximumOf(metric)
    raise ValueError(scalar_name)


def _parse_single_expression(
    raw_expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> MetricExpression:
    if raw_expression not in translated_metrics:
        with contextlib.suppress(ValueError):
            return _Constant(int(raw_expression))
        with contextlib.suppress(ValueError):
            return _Constant(float(raw_expression))

    var_name, consolidation = _extract_consolidation(raw_expression)
    if percent := var_name.endswith("(%)"):
        var_name = var_name[:-3]

    if ":" in var_name:
        var_name, scalar_name = var_name.split(":")
        metric = Metric(var_name, consolidation=consolidation)
        scalar = _from_scalar(scalar_name, metric)
        return _Percent(percent_value=scalar, base_value=_MaximumOf(metric)) if percent else scalar

    metric = Metric(var_name, consolidation=consolidation)
    return _Percent(percent_value=metric, base_value=_MaximumOf(metric)) if percent else metric


_RPNOperators = Literal["+", "*", "-", "/", "MIN", "MAX", "AVERAGE", "MERGE", ">", ">=", "<", "<="]


def _parse_expression(
    raw_expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> tuple[Sequence[MetricExpression | _RPNOperators], str, str]:
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

    stack: list[MetricExpression | _RPNOperators] = []
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
    stack: Sequence[MetricExpression | _RPNOperators],
) -> MetricExpression | ConditionalMetricExpression:
    resolved: list[MetricExpression | ConditionalMetricExpression] = []
    for element in stack:
        if isinstance(element, MetricExpression):
            resolved.append(element)
            continue

        if not isinstance(right := resolved.pop(), MetricExpression):
            raise TypeError(right)

        if not isinstance(left := resolved.pop(), MetricExpression):
            raise TypeError(left)

        match element:
            case "+":
                resolved.append(_Sum([left, right]))
            case "-":
                resolved.append(_Difference(minuend=left, subtrahend=right))
            case "*":
                resolved.append(_Product([left, right]))
            case "/":
                # Handle zero division by always adding a tiny bit to the divisor
                resolved.append(_Fraction(dividend=left, divisor=_Sum([right, _Constant(1e-16)])))
            case "MIN":
                resolved.append(_Minimum([left, right]))
            case "MAX":
                resolved.append(_Maximum([left, right]))
            case "AVERAGE":
                resolved.append(_Average([left, right]))
            case "MERGE":
                resolved.append(_Merge([left, right]))
            case ">=":
                resolved.append(GreaterEqualThan(left=left, right=right))
            case ">":
                resolved.append(GreaterThan(left=left, right=right))
            case "<=":
                resolved.append(LessEqualThan(left=left, right=right))
            case "<":
                resolved.append(LessThan(left=left, right=right))

    return resolved[0]


def _make_inner_metric_expression(expression: MetricExpression) -> MetricExpression:
    match expression:
        case _Constant():
            return Constant(expression.value)
        case _Metric():
            return Metric(expression.name, consolidation=expression.consolidation)
        case _WarningOf():
            return WarningOf(Metric(expression.metric.name))
        case _CriticalOf():
            return CriticalOf(Metric(expression.metric.name))
        case _MinimumOf():
            return MinimumOf(Metric(expression.metric.name))
        case _MaximumOf():
            return MaximumOf(Metric(expression.metric.name))
        case _Sum():
            return Sum([_make_inner_metric_expression(s) for s in expression.summands])
        case _Product():
            return Product([_make_inner_metric_expression(f) for f in expression.factors])
        case _Difference():
            return Difference(
                minuend=_make_inner_metric_expression(expression.minuend),
                subtrahend=_make_inner_metric_expression(expression.subtrahend),
            )
        case _Fraction():
            return Fraction(
                dividend=_make_inner_metric_expression(expression.dividend),
                divisor=_make_inner_metric_expression(expression.divisor),
            )
        case _Minimum():
            return Minimum([_make_inner_metric_expression(o) for o in expression.operands])
        case _Maximum():
            return Maximum([_make_inner_metric_expression(o) for o in expression.operands])
        case _Percent():
            return Percent(
                percent_value=_make_inner_metric_expression(expression.percent_value),
                base_value=_make_inner_metric_expression(expression.base_value),
            )
        case _Average():
            return Average([_make_inner_metric_expression(o) for o in expression.operands])
        case _Merge():
            return Merge([_make_inner_metric_expression(o) for o in expression.operands])
        case _:
            raise TypeError(expression)


def _make_metric_expression(
    expression: MetricExpression,
    unit_id: str,
    color: str,
) -> MetricExpression:
    match expression:
        case _Constant():
            return Constant(
                expression.value,
                unit_id=unit_id,
                color=color,
            )
        case _Metric():
            return Metric(
                expression.name,
                consolidation=expression.consolidation,
                unit_id=unit_id,
                color=color,
            )
        case _WarningOf():
            return WarningOf(
                Metric(expression.metric.name),
                unit_id=unit_id,
                color=color,
            )
        case _CriticalOf():
            return CriticalOf(
                Metric(expression.metric.name),
                unit_id=unit_id,
                color=color,
            )
        case _MinimumOf():
            return MinimumOf(
                Metric(expression.metric.name),
                unit_id=unit_id,
                color=color,
            )
        case _MaximumOf():
            return MaximumOf(
                Metric(expression.metric.name),
                unit_id=unit_id,
                color=color,
            )
        case _Sum():
            return Sum(
                [_make_inner_metric_expression(s) for s in expression.summands],
                unit_id=unit_id,
                color=color,
            )
        case _Product():
            return Product(
                [_make_inner_metric_expression(f) for f in expression.factors],
                unit_id=unit_id,
                color=color,
            )
        case _Difference():
            return Difference(
                minuend=_make_inner_metric_expression(expression.minuend),
                subtrahend=_make_inner_metric_expression(expression.subtrahend),
                unit_id=unit_id,
                color=color,
            )
        case _Fraction():
            return Fraction(
                dividend=_make_inner_metric_expression(expression.dividend),
                divisor=_make_inner_metric_expression(expression.divisor),
                unit_id=unit_id,
                color=color,
            )
        case _Minimum():
            return Minimum(
                [_make_inner_metric_expression(o) for o in expression.operands],
                unit_id=unit_id,
                color=color,
            )
        case _Maximum():
            return Maximum(
                [_make_inner_metric_expression(o) for o in expression.operands],
                unit_id=unit_id,
                color=color,
            )
        case _Percent():
            return Percent(
                percent_value=_make_inner_metric_expression(expression.percent_value),
                base_value=_make_inner_metric_expression(expression.base_value),
                unit_id=unit_id,
                color=color,
            )
        case _Average():
            return Average(
                [_make_inner_metric_expression(o) for o in expression.operands],
                unit_id=unit_id,
                color=color,
            )
        case _Merge():
            return Merge(
                [_make_inner_metric_expression(o) for o in expression.operands],
                unit_id=unit_id,
                color=color,
            )
        case _:
            return expression


def parse_expression(
    raw_expression: str | int | float,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> MetricExpression:
    if isinstance(raw_expression, (int, float)):
        return Constant(raw_expression)
    (
        stack,
        unit_id,
        color,
    ) = _parse_expression(raw_expression, translated_metrics)
    if isinstance(resolved := _resolve_stack(stack), MetricExpression):
        return _make_metric_expression(resolved, unit_id, color)
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
