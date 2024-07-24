#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import contextlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, KW_ONLY
from typing import Final, Literal

from cmk.utils.metrics import MetricName

from ._color import mix_colors, parse_color, render_color, scalar_colors
from ._loader import get_unit_info
from ._type_defs import GraphConsoldiationFunction, TranslatedMetric
from ._unit_info import unit_info, UnitInfo

# TODO CMK-15246 Checkmk 2.4: Remove legacy objects/RPNs


def _unit_mult(u1: UnitInfo, u2: UnitInfo) -> UnitInfo:
    # TODO: real unit computation!
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


def _make_unit_info(explicit_unit_name: str, unit_info_: UnitInfo) -> UnitInfo:
    return get_unit_info(explicit_unit_name) if explicit_unit_name else unit_info_


@dataclass(frozen=True)
class MetricExpressionResult:
    value: int | float
    unit_info: UnitInfo
    color: str


class MetricExpression(abc.ABC):
    @abc.abstractmethod
    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        raise NotImplementedError()

    @abc.abstractmethod
    def metrics(self) -> Iterator[Metric]:
        raise NotImplementedError()

    @abc.abstractmethod
    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        raise NotImplementedError()


@dataclass(frozen=True)
class Constant(MetricExpression):
    value: int | float
    _: KW_ONLY
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            self.value,
            _make_unit_info(
                self.explicit_unit_name,
                unit_info["count"] if isinstance(self.value, int) else unit_info[""],
            ),
            self.explicit_color or "#000000",
        )

    def metrics(self) -> Iterator[Metric]:
        yield from ()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from ()


@dataclass(frozen=True)
class Metric(MetricExpression):
    name: MetricName
    consolidation_func_name: GraphConsoldiationFunction | None = None
    _: KW_ONLY
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.name]["value"],
            _make_unit_info(
                self.explicit_unit_name,
                translated_metrics[self.name]["unit"],
            ),
            self.explicit_color or translated_metrics[self.name]["color"],
        )

    def metrics(self) -> Iterator[Metric]:
        yield self

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from ()


@dataclass(frozen=True)
class WarningOf(MetricExpression):
    metric: Metric
    name: Final = "warn"
    _: KW_ONLY
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name]["scalar"]["warn"],
            _make_unit_info(
                self.explicit_unit_name,
                self.metric.evaluate(translated_metrics).unit_info,
            ),
            self.explicit_color or scalar_colors.get("warn", "#808080"),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.metric.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield self


@dataclass(frozen=True)
class CriticalOf(MetricExpression):
    metric: Metric
    name: Final = "crit"
    _: KW_ONLY
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name]["scalar"]["crit"],
            _make_unit_info(
                self.explicit_unit_name,
                self.metric.evaluate(translated_metrics).unit_info,
            ),
            self.explicit_color or scalar_colors.get("crit", "#808080"),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.metric.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield self


@dataclass(frozen=True)
class MinimumOf(MetricExpression):
    metric: Metric
    name: Final = "min"
    _: KW_ONLY
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name]["scalar"]["min"],
            _make_unit_info(
                self.explicit_unit_name,
                self.metric.evaluate(translated_metrics).unit_info,
            ),
            self.explicit_color or scalar_colors.get("min", "#808080"),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.metric.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield self


@dataclass(frozen=True)
class MaximumOf(MetricExpression):
    metric: Metric
    name: Final = "max"
    _: KW_ONLY
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name]["scalar"]["max"],
            _make_unit_info(
                self.explicit_unit_name,
                self.metric.evaluate(translated_metrics).unit_info,
            ),
            self.explicit_color or scalar_colors.get("max", "#808080"),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.metric.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield self


@dataclass(frozen=True)
class Sum(MetricExpression):
    summands: Sequence[MetricExpression]
    _: KW_ONLY
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.summands) == 0:
            return MetricExpressionResult(
                0.0,
                _make_unit_info(
                    self.explicit_unit_name,
                    unit_info[""],
                ),
                self.explicit_color or "#000000",
            )

        first_result = self.summands[0].evaluate(translated_metrics)
        values = [first_result.value]
        unit_info_ = first_result.unit_info
        color = first_result.color
        for successor in self.summands[1:]:
            successor_result = successor.evaluate(translated_metrics)
            values.append(successor_result.value)
            unit_info_ = _unit_add(unit_info_, successor_result.unit_info)
            color = _choose_operator_color(color, successor_result.color)

        return MetricExpressionResult(
            sum(values),
            _make_unit_info(
                self.explicit_unit_name,
                unit_info_,
            ),
            self.explicit_color or color,
        )

    def metrics(self) -> Iterator[Metric]:
        yield from (m for s in self.summands for m in s.metrics())

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from (sc for s in self.summands for sc in s.scalars())


@dataclass(frozen=True)
class Product(MetricExpression):
    factors: Sequence[MetricExpression]
    _: KW_ONLY
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.factors) == 0:
            return MetricExpressionResult(
                1.0,
                _make_unit_info(
                    self.explicit_unit_name,
                    unit_info[""],
                ),
                self.explicit_color or "#000000",
            )

        first_result = self.factors[0].evaluate(translated_metrics)
        product = first_result.value
        unit_info_ = first_result.unit_info
        color = first_result.color
        for successor in self.factors[1:]:
            successor_result = successor.evaluate(translated_metrics)
            product *= successor_result.value
            unit_info_ = _unit_mult(unit_info_, successor_result.unit_info)
            color = _choose_operator_color(color, successor_result.color)

        return MetricExpressionResult(
            product,
            _make_unit_info(
                self.explicit_unit_name,
                unit_info_,
            ),
            self.explicit_color or color,
        )

    def metrics(self) -> Iterator[Metric]:
        yield from (m for f in self.factors for m in f.metrics())

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from (s for f in self.factors for s in f.scalars())


@dataclass(frozen=True, kw_only=True)
class Difference(MetricExpression):
    minuend: MetricExpression
    subtrahend: MetricExpression
    explicit_unit_name: str = ""
    explicit_color: str = ""

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
            _make_unit_info(
                self.explicit_unit_name,
                _unit_sub(minuend_result.unit_info, subtrahend_result.unit_info),
            ),
            (
                self.explicit_color
                or _choose_operator_color(minuend_result.color, subtrahend_result.color)
            ),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.minuend.metrics()
        yield from self.subtrahend.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from self.minuend.scalars()
        yield from self.subtrahend.scalars()


@dataclass(frozen=True, kw_only=True)
class Fraction(MetricExpression):
    dividend: MetricExpression
    divisor: MetricExpression
    explicit_unit_name: str = ""
    explicit_color: str = ""

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
            _make_unit_info(
                self.explicit_unit_name,
                _unit_div(dividend_result.unit_info, divisor_result.unit_info),
            ),
            (
                self.explicit_color
                or _choose_operator_color(dividend_result.color, divisor_result.color)
            ),
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.dividend.metrics()
        yield from self.divisor.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from self.dividend.scalars()
        yield from self.divisor.scalars()


@dataclass(frozen=True)
class Minimum(MetricExpression):
    operands: Sequence[MetricExpression]
    _: KW_ONLY
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(
                float("nan"),
                _make_unit_info(
                    self.explicit_unit_name,
                    unit_info[""],
                ),
                self.explicit_color or "#000000",
            )

        minimum = self.operands[0].evaluate(translated_metrics)
        for operand in self.operands[1:]:
            operand_result = operand.evaluate(translated_metrics)
            if operand_result.value < minimum.value:
                minimum = operand_result

        return minimum

    def metrics(self) -> Iterator[Metric]:
        yield from (m for o in self.operands for m in o.metrics())

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from (s for o in self.operands for s in o.scalars())


@dataclass(frozen=True)
class Maximum(MetricExpression):
    operands: Sequence[MetricExpression]
    _: KW_ONLY
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(
                float("nan"),
                _make_unit_info(
                    self.explicit_unit_name,
                    unit_info[""],
                ),
                self.explicit_color or "#000000",
            )

        maximum = self.operands[0].evaluate(translated_metrics)
        for operand in self.operands[1:]:
            operand_result = operand.evaluate(translated_metrics)
            if operand_result.value > maximum.value:
                maximum = operand_result

        return maximum

    def metrics(self) -> Iterator[Metric]:
        yield from (m for o in self.operands for m in o.metrics())

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from (s for o in self.operands for s in o.scalars())


# Composed metric declarations:


@dataclass(frozen=True, kw_only=True)
class Percent(MetricExpression):
    """percentage = 100 * percent_value / base_value"""

    percent_value: MetricExpression
    base_value: MetricExpression
    explicit_unit_name: str = ""
    explicit_color: str = ""

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
            _make_unit_info(
                self.explicit_unit_name,
                unit_info["%"],
            ),
            self.explicit_color or self.percent_value.evaluate(translated_metrics).color,
        )

    def metrics(self) -> Iterator[Metric]:
        yield from self.percent_value.metrics()
        yield from self.base_value.metrics()

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from self.percent_value.scalars()
        yield from self.base_value.scalars()


# Special metric declarations for custom graphs


@dataclass(frozen=True)
class Average(MetricExpression):
    operands: Sequence[MetricExpression]
    _: KW_ONLY
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(
                float("nan"),
                _make_unit_info(
                    self.explicit_unit_name,
                    unit_info[""],
                ),
                self.explicit_color or "#000000",
            )

        result = Sum(self.operands).evaluate(translated_metrics)
        return MetricExpressionResult(
            result.value / len(self.operands),
            _make_unit_info(
                self.explicit_unit_name,
                result.unit_info,
            ),
            self.explicit_color or result.color,
        )

    def metrics(self) -> Iterator[Metric]:
        yield from (m for o in self.operands for m in o.metrics())

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from (s for o in self.operands for s in o.scalars())


@dataclass(frozen=True)
class Merge(MetricExpression):
    operands: Sequence[MetricExpression]
    _: KW_ONLY
    explicit_unit_name: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        # TODO None?
        for operand in self.operands:
            if (result := operand.evaluate(translated_metrics)).value is not None:
                return result
        return MetricExpressionResult(
            float("nan"),
            _make_unit_info(
                self.explicit_unit_name,
                unit_info[""],
            ),
            self.explicit_color or "#000000",
        )

    def metrics(self) -> Iterator[Metric]:
        yield from (m for o in self.operands for m in o.metrics())

    def scalars(self) -> Iterator[WarningOf | CriticalOf | MinimumOf | MaximumOf]:
        yield from (s for o in self.operands for s in o.scalars())


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
    translated_metrics: Mapping[str, TranslatedMetric],
) -> MetricExpression:
    if expression not in translated_metrics:
        with contextlib.suppress(ValueError):
            return Constant(int(expression))
        with contextlib.suppress(ValueError):
            return Constant(float(expression))

    var_name, consolidation_func_name = _extract_consolidation_func_name(expression)
    if percent := var_name.endswith("(%)"):
        var_name = var_name[:-3]

    if ":" in var_name:
        var_name, scalar_name = var_name.split(":")
        metric = Metric(var_name, consolidation_func_name)
        scalar = _from_scalar(scalar_name, metric)
        return Percent(percent_value=scalar, base_value=MaximumOf(metric)) if percent else scalar

    metric = Metric(var_name, consolidation_func_name)
    return Percent(percent_value=metric, base_value=MaximumOf(metric)) if percent else metric


RPNOperators = Literal["+", "*", "-", "/", "MIN", "MAX", "AVERAGE", "MERGE", ">", ">=", "<", "<="]


def _parse_expression(
    expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> tuple[Sequence[MetricExpression | RPNOperators], str, str]:
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

    explicit_color = ""
    if "#" in expression:
        expression, explicit_color_ = expression.rsplit("#", 1)  # drop appended color information
        explicit_color = f"#{explicit_color_}"

    explicit_unit_name = ""
    if "@" in expression:
        expression, explicit_unit_name = expression.rsplit("@", 1)  # appended unit name

    stack: list[MetricExpression | RPNOperators] = []
    for p in expression.split(","):
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
                stack.append(
                    _parse_single_expression(
                        p,
                        translated_metrics,
                    )
                )

    return stack, explicit_unit_name, explicit_color


def _resolve_stack(
    stack: Sequence[MetricExpression | RPNOperators],
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


def _add_explicit_unit_name_or_color(
    expression: MetricExpression, explicit_unit_name: str, explicit_color: str
) -> MetricExpression:
    match expression:
        case Constant():
            return Constant(
                expression.value,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case Metric():
            return Metric(
                expression.name,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case WarningOf():
            return WarningOf(
                expression.metric,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case CriticalOf():
            return CriticalOf(
                expression.metric,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case MinimumOf():
            return MinimumOf(
                expression.metric,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case MaximumOf():
            return MaximumOf(
                expression.metric,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case Sum():
            return Sum(
                expression.summands,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case Product():
            return Product(
                expression.factors,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case Difference():
            return Difference(
                minuend=expression.minuend,
                subtrahend=expression.subtrahend,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case Fraction():
            return Fraction(
                dividend=expression.dividend,
                divisor=expression.divisor,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case Minimum():
            return Minimum(
                expression.operands,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case Maximum():
            return Maximum(
                expression.operands,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case Percent():
            return Percent(
                percent_value=expression.percent_value,
                base_value=expression.base_value,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case Average():
            return Average(
                expression.operands,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
        case Merge():
            return Merge(
                expression.operands,
                explicit_unit_name=explicit_unit_name,
                explicit_color=explicit_color,
            )
    assert False, expression


def parse_expression(
    expression: str | int | float,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> MetricExpression:
    if isinstance(expression, (int, float)):
        return Constant(expression)

    (
        stack,
        explicit_unit_name,
        explicit_color,
    ) = _parse_expression(expression, translated_metrics)

    if isinstance(resolved := _resolve_stack(stack), MetricExpression):
        return (
            _add_explicit_unit_name_or_color(resolved, explicit_unit_name, explicit_color)
            if explicit_unit_name or explicit_color
            else resolved
        )
    raise TypeError(resolved)


def parse_conditional_expression(
    expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> ConditionalMetricExpression:
    (
        stack,
        _explicit_unit_name,
        _explicit_color,
    ) = _parse_expression(expression, translated_metrics)

    if isinstance(
        resolved := _resolve_stack(stack),
        ConditionalMetricExpression,
    ):
        return resolved
    raise TypeError(resolved)


def has_required_metrics_or_scalars(
    expressions: Sequence[MetricExpression],
    translated_metrics: Mapping[str, TranslatedMetric],
) -> bool:
    for expression in expressions:
        for metric in expression.metrics():
            if metric.name not in translated_metrics:
                return False
        for scalar in expression.scalars():
            if scalar.metric.name not in translated_metrics:
                return False
            # TODO: scalar has type "WarningOf | CriticalOf | MinimumOf | MaximumOf" and these types
            # meet at MetricExpression. But MetricExpression has no "name" attribute. This should
            # be done differently either by introduing another class (the common superclass of those
            # types) or by a protocol.
            if scalar.name not in translated_metrics[scalar.metric.name]["scalar"]:  # type: ignore[operator]
                return False
    return True
