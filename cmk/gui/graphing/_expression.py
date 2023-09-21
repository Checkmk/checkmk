#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import assert_never, Callable, Literal

from cmk.utils.metrics import MetricName

from cmk.gui.type_defs import TranslatedMetrics, UnitInfo

from ._color import mix_colors, parse_color, render_color, scalar_colors
from ._type_defs import GraphConsoldiationFunction
from ._unit_info import unit_info


# TODO: real unit computation!
def _unit_mult(u1: UnitInfo, u2: UnitInfo) -> UnitInfo:
    return u2 if u1 in (unit_info[""], unit_info["count"]) else u1


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
    value: float
    unit_info: UnitInfo
    color: str


class MetricDeclaration(abc.ABC):
    @abc.abstractmethod
    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        raise NotImplementedError()

    @abc.abstractmethod
    def metrics(self) -> Iterator[Metric]:
        raise NotImplementedError()


@dataclass(frozen=True)
class ConstantInt(MetricDeclaration):
    value: int

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        return MetricExpressionResult(float(self.value), unit_info["count"], "#000000")

    def metrics(self) -> Iterator[Metric]:
        yield from ()


@dataclass(frozen=True)
class ConstantFloat(MetricDeclaration):
    value: float

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        return MetricExpressionResult(self.value, unit_info[""], "#000000")

    def metrics(self) -> Iterator[Metric]:
        yield from ()


@dataclass(frozen=True)
class Metric(MetricDeclaration):
    name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None = None

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.name]["value"],
            translated_metrics[self.name]["unit"],
            translated_metrics[self.name]["color"],
        )

    def metrics(self) -> Iterator[Metric]:
        yield self


@dataclass(frozen=True)
class WarningOf(MetricDeclaration):
    metric: Metric

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name]["scalar"]["warn"],
            self.metric.evaluate(translated_metrics).unit_info,
            scalar_colors.get("warn", "#808080"),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.metric.metrics()


@dataclass(frozen=True)
class CriticalOf(MetricDeclaration):
    metric: Metric

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name]["scalar"]["crit"],
            self.metric.evaluate(translated_metrics).unit_info,
            scalar_colors.get("crit", "#808080"),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.metric.metrics()


@dataclass(frozen=True)
class MinimumOf(MetricDeclaration):
    metric: Metric

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name]["scalar"]["min"],
            self.metric.evaluate(translated_metrics).unit_info,
            scalar_colors.get("min", "#808080"),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.metric.metrics()


@dataclass(frozen=True)
class MaximumOf(MetricDeclaration):
    metric: Metric

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name]["scalar"]["max"],
            self.metric.evaluate(translated_metrics).unit_info,
            scalar_colors.get("max", "#808080"),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.metric.metrics()


@dataclass(frozen=True)
class Sum(MetricDeclaration):
    summands: Sequence[MetricDeclaration]

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
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

    def metrics(self) -> Iterator[Metric]:
        yield from (m for s in self.summands for m in s.metrics())


@dataclass(frozen=True)
class Product(MetricDeclaration):
    factors: Sequence[MetricDeclaration]

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
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

    def metrics(self) -> Iterator[Metric]:
        yield from (m for f in self.factors for m in f.metrics())


@dataclass(frozen=True, kw_only=True)
class Difference(MetricDeclaration):
    minuend: MetricDeclaration
    subtrahend: MetricDeclaration

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
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

    def metrics(self) -> Iterator[Metric]:
        yield from self.minuend.metrics()
        yield from self.subtrahend.metrics()


@dataclass(frozen=True, kw_only=True)
class Fraction(MetricDeclaration):
    dividend: MetricDeclaration
    divisor: MetricDeclaration

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
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

    def metrics(self) -> Iterator[Metric]:
        yield from self.dividend.metrics()
        yield from self.divisor.metrics()


@dataclass(frozen=True, kw_only=True)
class GreaterThan(MetricDeclaration):
    left: MetricDeclaration
    right: MetricDeclaration

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        return MetricExpressionResult(
            (
                1.0
                if self.left.evaluate(translated_metrics).value
                > self.right.evaluate(translated_metrics).value
                else 0.0
            ),
            unit_info[""],
            "#000000",
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.left.metrics()
        yield from self.right.metrics()


@dataclass(frozen=True, kw_only=True)
class GreaterEqualThan(MetricDeclaration):
    left: MetricDeclaration
    right: MetricDeclaration

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        return MetricExpressionResult(
            (
                1.0
                if self.left.evaluate(translated_metrics).value
                >= self.right.evaluate(translated_metrics).value
                else 0.0
            ),
            unit_info[""],
            "#000000",
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.left.metrics()
        yield from self.right.metrics()


@dataclass(frozen=True, kw_only=True)
class LessThan(MetricDeclaration):
    left: MetricDeclaration
    right: MetricDeclaration

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        return MetricExpressionResult(
            (
                1.0
                if self.left.evaluate(translated_metrics).value
                < self.right.evaluate(translated_metrics).value
                else 0.0
            ),
            unit_info[""],
            "#000000",
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.left.metrics()
        yield from self.right.metrics()


@dataclass(frozen=True, kw_only=True)
class LessEqualThan(MetricDeclaration):
    left: MetricDeclaration
    right: MetricDeclaration

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        return MetricExpressionResult(
            (
                1.0
                if self.left.evaluate(translated_metrics).value
                <= self.right.evaluate(translated_metrics).value
                else 0.0
            ),
            unit_info[""],
            "#000000",
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.left.metrics()
        yield from self.right.metrics()


@dataclass(frozen=True)
class Minimum(MetricDeclaration):
    operands: Sequence[MetricDeclaration]

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(float("nan"), unit_info[""], "#000000")

        minimum = self.operands[0].evaluate(translated_metrics)
        for operand in self.operands[1:]:
            operand_result = operand.evaluate(translated_metrics)
            if operand_result.value < minimum.value:
                minimum = operand_result

        return minimum

    def metrics(self) -> Iterator[Metric]:
        yield from (m for o in self.operands for m in o.metrics())


@dataclass(frozen=True)
class Maximum(MetricDeclaration):
    operands: Sequence[MetricDeclaration]

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(float("nan"), unit_info[""], "#000000")

        maximum = self.operands[0].evaluate(translated_metrics)
        for operand in self.operands[1:]:
            operand_result = operand.evaluate(translated_metrics)
            if operand_result.value > maximum.value:
                maximum = operand_result

        return maximum

    def metrics(self) -> Iterator[Metric]:
        yield from (m for o in self.operands for m in o.metrics())


# Composed metric declarations:


@dataclass(frozen=True, kw_only=True)
class Percent(MetricDeclaration):
    reference: MetricDeclaration
    metric: Metric

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        return MetricExpressionResult(
            (
                Fraction(
                    dividend=Product([ConstantFloat(100.0), self.reference]),
                    divisor=MaximumOf(self.metric),
                )
                .evaluate(translated_metrics)
                .value
            ),
            unit_info["%"],
            self.reference.evaluate(translated_metrics).color,
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.reference.metrics()
        yield from self.metric.metrics()


# Special metric declarations for custom graphs


@dataclass(frozen=True)
class Average(MetricDeclaration):
    operands: Sequence[MetricDeclaration]

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(float("nan"), unit_info[""], "#000000")

        result = Sum(self.operands).evaluate(translated_metrics)
        return MetricExpressionResult(
            result.value / len(self.operands),
            result.unit_info,
            result.color,
        )

    def metrics(self) -> Iterator[Metric]:
        yield from (m for o in self.operands for m in o.metrics())


@dataclass(frozen=True)
class Merge(MetricDeclaration):
    operands: Sequence[MetricDeclaration]

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        # TODO None?
        for operand in self.operands:
            if (result := operand.evaluate(translated_metrics)).value is not None:
                return result
        return MetricExpressionResult(float("nan"), unit_info[""], "#000000")

    def metrics(self) -> Iterator[Metric]:
        yield from (m for o in self.operands for m in o.metrics())


RPNOperators = Literal["+", "*", "-", "/", ">", ">=", "<", "<=", "MIN", "MAX", "AVERAGE", "MERGE"]


def _apply_operator(
    operator: RPNOperators, left: MetricDeclaration, right: MetricDeclaration
) -> MetricDeclaration:
    # TODO: Do real unit computation, detect non-matching units
    match operator:
        case "+":
            return Sum([left, right])
        case "-":
            return Difference(minuend=left, subtrahend=right)
        case "*":
            return Product([left, right])
        case "/":
            # Handle zero division by always adding a tiny bit to the divisor
            return Fraction(dividend=left, divisor=Sum([right, ConstantFloat(1e-16)]))
        case ">":
            return GreaterThan(left=left, right=right)
        case ">=":
            return GreaterEqualThan(left=left, right=right)
        case "<":
            return LessThan(left=left, right=right)
        case "<=":
            return LessEqualThan(left=left, right=right)
        case "MIN":
            return Minimum([left, right])
        case "MAX":
            return Maximum([left, right])
        case "AVERAGE":
            return Average([left, right])
        case "MERGE":
            return Merge([left, right])
    assert_never(operator)


def _extract_consolidation_func_name(
    expression: str,
) -> tuple[str, GraphConsoldiationFunction | None]:
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
    expression: str,
    translated_metrics: TranslatedMetrics,
    enforced_consolidation_func_name: GraphConsoldiationFunction | None,
) -> MetricDeclaration:
    if expression not in translated_metrics:
        try:
            return ConstantInt(int(expression))
        except ValueError:
            pass

        try:
            return ConstantFloat(float(expression))
        except ValueError:
            pass

    var_name, consolidation_func_name = _extract_consolidation_func_name(expression)
    if percent := var_name.endswith("(%)"):
        var_name = var_name[:-3]

    if ":" in var_name:
        var_name, scalar_name = var_name.split(":")
        metric = Metric(var_name, consolidation_func_name or enforced_consolidation_func_name)
        reference = _from_scalar(scalar_name, metric)
        return Percent(reference=reference, metric=metric) if percent else reference

    metric = Metric(var_name, consolidation_func_name or enforced_consolidation_func_name)
    return Percent(reference=metric, metric=metric) if percent else metric


@dataclass(frozen=True)
class MetricExpression:
    declaration: MetricDeclaration
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(self, translated_metrics: TranslatedMetrics) -> MetricExpressionResult:
        result = self.declaration.evaluate(translated_metrics)
        return MetricExpressionResult(
            result.value,
            unit_info[self.explicit_unit_name] if self.explicit_unit_name else result.unit_info,
            "#" + self.explicit_color if self.explicit_color else result.color,
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.declaration.metrics()


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
def parse_expression(
    expression: str | int | float,
    translated_metrics: TranslatedMetrics,
    enforced_consolidation_func_name: GraphConsoldiationFunction | None = None,
) -> MetricExpression:
    if isinstance(expression, int):
        return MetricExpression(ConstantInt(expression))

    if isinstance(expression, float):
        return MetricExpression(ConstantFloat(expression))

    explicit_color = ""
    if "#" in expression:
        expression, explicit_color = expression.rsplit("#", 1)  # drop appended color information

    explicit_unit_name = ""
    if "@" in expression:
        expression, explicit_unit_name = expression.rsplit("@", 1)  # appended unit name

    if len(parts := expression.split(",")) == 1:
        return MetricExpression(
            _parse_single_expression(
                parts[0],
                translated_metrics,
                enforced_consolidation_func_name,
            ),
            explicit_unit_name,
            explicit_color,
        )

    operators: list[RPNOperators] = []
    operands = []
    for p in parts:
        match p:
            case "+":
                operators.append("+")
            case "-":
                operators.append("-")
            case "*":
                operators.append("*")
            case "/":
                operators.append("/")
            case ">":
                operators.append(">")
            case ">=":
                operators.append(">=")
            case "<":
                operators.append("<")
            case "<=":
                operators.append("<=")
            case "MIN":
                operators.append("MIN")
            case "MAX":
                operators.append("MAX")
            case "AVERAGE":
                operators.append("AVERAGE")
            case "MERGE":
                operators.append("MERGE")
            case _:
                operands.append(p)

    if len(operators) != (len(operands) - 1):
        # "a,b,+,c,-,..." -> operators = ["+", "-", ...], operands = ["a", "b", "c", ...]
        raise ValueError(f"Too few or many operators {operators!r} for {operands!r}")

    operand = _apply_operator(
        operators.pop(0),
        _parse_single_expression(
            operands.pop(0),
            translated_metrics,
            enforced_consolidation_func_name,
        ),
        _parse_single_expression(
            operands.pop(0),
            translated_metrics,
            enforced_consolidation_func_name,
        ),
    )
    while operands:
        operand = _apply_operator(
            operators.pop(0),
            operand,
            _parse_single_expression(
                operands.pop(0),
                translated_metrics,
                enforced_consolidation_func_name,
            ),
        )

    return MetricExpression(operand, explicit_unit_name, explicit_color)
