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
from ._type_defs import GraphConsolidationFunction

# TODO CMK-15246 Checkmk 2.4: Remove legacy objects/RPNs


class _MetricExpression:
    pass


@dataclass(frozen=True)
class _Constant(_MetricExpression):
    value: int | float


@dataclass(frozen=True)
class _Metric(_MetricExpression):
    name: MetricName
    consolidation: GraphConsolidationFunction | None = None


@dataclass(frozen=True)
class _WarningOf(_MetricExpression):
    metric: _Metric


@dataclass(frozen=True)
class _CriticalOf(_MetricExpression):
    metric: _Metric


@dataclass(frozen=True)
class _MinimumOf(_MetricExpression):
    metric: _Metric


@dataclass(frozen=True)
class _MaximumOf(_MetricExpression):
    metric: _Metric


@dataclass(frozen=True)
class _Sum(_MetricExpression):
    summands: Sequence[_MetricExpression]


@dataclass(frozen=True)
class _Product(_MetricExpression):
    factors: Sequence[_MetricExpression]


@dataclass(frozen=True, kw_only=True)
class _Difference(_MetricExpression):
    minuend: _MetricExpression
    subtrahend: _MetricExpression


@dataclass(frozen=True, kw_only=True)
class _Fraction(_MetricExpression):
    dividend: _MetricExpression
    divisor: _MetricExpression


@dataclass(frozen=True)
class _Minimum(_MetricExpression):
    operands: Sequence[_MetricExpression]


@dataclass(frozen=True)
class _Maximum(_MetricExpression):
    operands: Sequence[_MetricExpression]


@dataclass(frozen=True, kw_only=True)
class _Percent(_MetricExpression):
    """percentage = 100 * percent_value / base_value"""

    percent_value: _MetricExpression
    base_value: _MetricExpression


@dataclass(frozen=True)
class _Average(_MetricExpression):
    operands: Sequence[_MetricExpression]


@dataclass(frozen=True)
class _Merge(_MetricExpression):
    operands: Sequence[_MetricExpression]


class _ConditionalMetricExpression(abc.ABC):
    pass


@dataclass(frozen=True, kw_only=True)
class _GreaterThan(_ConditionalMetricExpression):
    left: _MetricExpression
    right: _MetricExpression


@dataclass(frozen=True, kw_only=True)
class _GreaterEqualThan(_ConditionalMetricExpression):
    left: _MetricExpression
    right: _MetricExpression


@dataclass(frozen=True, kw_only=True)
class _LessThan(_ConditionalMetricExpression):
    left: _MetricExpression
    right: _MetricExpression


@dataclass(frozen=True, kw_only=True)
class _LessEqualThan(_ConditionalMetricExpression):
    left: _MetricExpression
    right: _MetricExpression


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
    scalar_name: str, metric: _Metric
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
) -> _MetricExpression:
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
        metric = _Metric(var_name, consolidation=consolidation)
        scalar = _from_scalar(scalar_name, metric)
        return _Percent(percent_value=scalar, base_value=_MaximumOf(metric)) if percent else scalar

    metric = _Metric(var_name, consolidation=consolidation)
    return _Percent(percent_value=metric, base_value=_MaximumOf(metric)) if percent else metric


_RPNOperators = Literal["+", "*", "-", "/", "MIN", "MAX", "AVERAGE", "MERGE", ">", ">=", "<", "<="]


def _parse_expression(
    raw_expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> tuple[Sequence[_MetricExpression | _RPNOperators], str, str]:
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
    if "#" in raw_expression:
        # drop appended color information
        raw_expression, explicit_color_ = raw_expression.rsplit("#", 1)
        explicit_color = f"#{explicit_color_}"

    explicit_unit_id = ""
    if "@" in raw_expression:
        # appended unit name
        raw_expression, explicit_unit_id = raw_expression.rsplit("@", 1)

    stack: list[_MetricExpression | _RPNOperators] = []
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

    return stack, explicit_unit_id, explicit_color


def _resolve_stack(
    stack: Sequence[_MetricExpression | _RPNOperators],
) -> _MetricExpression | _ConditionalMetricExpression:
    resolved: list[_MetricExpression | _ConditionalMetricExpression] = []
    for element in stack:
        if isinstance(element, _MetricExpression):
            resolved.append(element)
            continue

        if not isinstance(right := resolved.pop(), _MetricExpression):
            raise TypeError(right)

        if not isinstance(left := resolved.pop(), _MetricExpression):
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
                resolved.append(_GreaterEqualThan(left=left, right=right))
            case ">":
                resolved.append(_GreaterThan(left=left, right=right))
            case "<=":
                resolved.append(_LessEqualThan(left=left, right=right))
            case "<":
                resolved.append(_LessThan(left=left, right=right))

    return resolved[0]


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
class Constant(MetricExpression):
    value: int | float
    _: KW_ONLY
    explicit_unit_id: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if self.explicit_unit_id:
            unit_info_ = get_unit_info(self.explicit_unit_id)
        elif isinstance(self.value, int):
            unit_info_ = unit_info["count"]
        else:
            unit_info_ = unit_info[""]
        return MetricExpressionResult(
            self.value,
            unit_info_,
            self.explicit_color or "#000000",
        )

    def metric_names(self) -> Iterator[str]:
        yield from ()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from ()


@dataclass(frozen=True)
class Metric(MetricExpression):
    name: MetricName
    _: KW_ONLY
    consolidation: GraphConsolidationFunction | None = None
    explicit_unit_id: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.name].value,
            (
                get_unit_info(self.explicit_unit_id)
                if self.explicit_unit_id
                else translated_metrics[self.name].unit_info
            ),
            self.explicit_color or translated_metrics[self.name].color,
        )

    def metric_names(self) -> Iterator[str]:
        yield self.name

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from ()


@dataclass(frozen=True)
class WarningOf(MetricExpression):
    metric: Metric
    _: KW_ONLY
    explicit_unit_id: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name].scalar["warn"],
            (
                get_unit_info(self.explicit_unit_id)
                if self.explicit_unit_id
                else self.metric.evaluate(translated_metrics).unit_info
            ),
            self.explicit_color or scalar_colors.get("warn", "#808080"),
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.metric.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield ScalarName(self.metric.name, "warn")


@dataclass(frozen=True)
class CriticalOf(MetricExpression):
    metric: Metric
    _: KW_ONLY
    explicit_unit_id: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name].scalar["crit"],
            (
                get_unit_info(self.explicit_unit_id)
                if self.explicit_unit_id
                else self.metric.evaluate(translated_metrics).unit_info
            ),
            self.explicit_color or scalar_colors.get("crit", "#808080"),
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.metric.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield ScalarName(self.metric.name, "crit")


@dataclass(frozen=True)
class MinimumOf(MetricExpression):
    metric: Metric
    _: KW_ONLY
    explicit_unit_id: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name].scalar["min"],
            (
                get_unit_info(self.explicit_unit_id)
                if self.explicit_unit_id
                else self.metric.evaluate(translated_metrics).unit_info
            ),
            self.explicit_color or scalar_colors.get("min", "#808080"),
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.metric.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield ScalarName(self.metric.name, "min")


@dataclass(frozen=True)
class MaximumOf(MetricExpression):
    metric: Metric
    _: KW_ONLY
    explicit_unit_id: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        return MetricExpressionResult(
            translated_metrics[self.metric.name].scalar["max"],
            (
                get_unit_info(self.explicit_unit_id)
                if self.explicit_unit_id
                else self.metric.evaluate(translated_metrics).unit_info
            ),
            self.explicit_color or scalar_colors.get("max", "#808080"),
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.metric.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield ScalarName(self.metric.name, "max")


@dataclass(frozen=True)
class Sum(MetricExpression):
    summands: Sequence[MetricExpression]
    _: KW_ONLY
    explicit_unit_id: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.summands) == 0:
            return MetricExpressionResult(
                0.0,
                get_unit_info(self.explicit_unit_id) if self.explicit_unit_id else unit_info[""],
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
            get_unit_info(self.explicit_unit_id) if self.explicit_unit_id else unit_info_,
            self.explicit_color or color,
        )

    def metric_names(self) -> Iterator[str]:
        yield from (n for s in self.summands for n in s.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for s in self.summands for n in s.scalar_names())


@dataclass(frozen=True)
class Product(MetricExpression):
    factors: Sequence[MetricExpression]
    _: KW_ONLY
    explicit_unit_id: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.factors) == 0:
            return MetricExpressionResult(
                1.0,
                get_unit_info(self.explicit_unit_id) if self.explicit_unit_id else unit_info[""],
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
            get_unit_info(self.explicit_unit_id) if self.explicit_unit_id else unit_info_,
            self.explicit_color or color,
        )

    def metric_names(self) -> Iterator[str]:
        yield from (n for f in self.factors for n in f.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for f in self.factors for n in f.scalar_names())


@dataclass(frozen=True, kw_only=True)
class Difference(MetricExpression):
    minuend: MetricExpression
    subtrahend: MetricExpression
    explicit_unit_id: str = ""
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
            (
                get_unit_info(self.explicit_unit_id)
                if self.explicit_unit_id
                else _unit_sub(minuend_result.unit_info, subtrahend_result.unit_info)
            ),
            (
                self.explicit_color
                or _choose_operator_color(minuend_result.color, subtrahend_result.color)
            ),
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.minuend.metric_names()
        yield from self.subtrahend.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from self.minuend.scalar_names()
        yield from self.subtrahend.scalar_names()


@dataclass(frozen=True, kw_only=True)
class Fraction(MetricExpression):
    dividend: MetricExpression
    divisor: MetricExpression
    explicit_unit_id: str = ""
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
            (
                get_unit_info(self.explicit_unit_id)
                if self.explicit_unit_id
                else _unit_div(dividend_result.unit_info, divisor_result.unit_info)
            ),
            (
                self.explicit_color
                or _choose_operator_color(dividend_result.color, divisor_result.color)
            ),
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.dividend.metric_names()
        yield from self.divisor.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from self.dividend.scalar_names()
        yield from self.divisor.scalar_names()


@dataclass(frozen=True)
class Minimum(MetricExpression):
    operands: Sequence[MetricExpression]
    _: KW_ONLY
    explicit_unit_id: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(
                float("nan"),
                get_unit_info(self.explicit_unit_id) if self.explicit_unit_id else unit_info[""],
                self.explicit_color or "#000000",
            )

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
class Maximum(MetricExpression):
    operands: Sequence[MetricExpression]
    _: KW_ONLY
    explicit_unit_id: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(
                float("nan"),
                get_unit_info(self.explicit_unit_id) if self.explicit_unit_id else unit_info[""],
                self.explicit_color or "#000000",
            )

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
class Percent(MetricExpression):
    """percentage = 100 * percent_value / base_value"""

    percent_value: MetricExpression
    base_value: MetricExpression
    explicit_unit_id: str = ""
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
            get_unit_info(self.explicit_unit_id) if self.explicit_unit_id else unit_info["%"],
            self.explicit_color or self.percent_value.evaluate(translated_metrics).color,
        )

    def metric_names(self) -> Iterator[str]:
        yield from self.percent_value.metric_names()
        yield from self.base_value.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from self.percent_value.scalar_names()
        yield from self.base_value.scalar_names()


# Special metric declarations for custom graphs


@dataclass(frozen=True)
class Average(MetricExpression):
    operands: Sequence[MetricExpression]
    _: KW_ONLY
    explicit_unit_id: str = ""
    explicit_color: str = ""

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> MetricExpressionResult:
        if len(self.operands) == 0:
            return MetricExpressionResult(
                float("nan"),
                get_unit_info(self.explicit_unit_id) if self.explicit_unit_id else unit_info[""],
                self.explicit_color or "#000000",
            )

        result = Sum(self.operands).evaluate(translated_metrics)
        return MetricExpressionResult(
            result.value / len(self.operands),
            get_unit_info(self.explicit_unit_id) if self.explicit_unit_id else result.unit_info,
            self.explicit_color or result.color,
        )

    def metric_names(self) -> Iterator[str]:
        yield from (n for o in self.operands for n in o.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for o in self.operands for n in o.scalar_names())


@dataclass(frozen=True)
class Merge(MetricExpression):
    operands: Sequence[MetricExpression]
    _: KW_ONLY
    explicit_unit_id: str = ""
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
            get_unit_info(self.explicit_unit_id) if self.explicit_unit_id else unit_info[""],
            self.explicit_color or "#000000",
        )

    def metric_names(self) -> Iterator[str]:
        yield from (n for o in self.operands for n in o.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for o in self.operands for n in o.scalar_names())


def _make_inner_metric_expression(
    expression: _MetricExpression | _ConditionalMetricExpression,
) -> MetricExpression:
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
    expression: _MetricExpression | _ConditionalMetricExpression,
    explicit_unit_id: str,
    explicit_color: str,
) -> MetricExpression:
    match expression:
        case _Constant():
            return Constant(
                expression.value,
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _Metric():
            return Metric(
                expression.name,
                consolidation=expression.consolidation,
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _WarningOf():
            return WarningOf(
                Metric(expression.metric.name),
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _CriticalOf():
            return CriticalOf(
                Metric(expression.metric.name),
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _MinimumOf():
            return MinimumOf(
                Metric(expression.metric.name),
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _MaximumOf():
            return MaximumOf(
                Metric(expression.metric.name),
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _Sum():
            return Sum(
                [_make_inner_metric_expression(s) for s in expression.summands],
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _Product():
            return Product(
                [_make_inner_metric_expression(f) for f in expression.factors],
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _Difference():
            return Difference(
                minuend=_make_inner_metric_expression(expression.minuend),
                subtrahend=_make_inner_metric_expression(expression.subtrahend),
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _Fraction():
            return Fraction(
                dividend=_make_inner_metric_expression(expression.dividend),
                divisor=_make_inner_metric_expression(expression.divisor),
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _Minimum():
            return Minimum(
                [_make_inner_metric_expression(o) for o in expression.operands],
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _Maximum():
            return Maximum(
                [_make_inner_metric_expression(o) for o in expression.operands],
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _Percent():
            return Percent(
                percent_value=_make_inner_metric_expression(expression.percent_value),
                base_value=_make_inner_metric_expression(expression.base_value),
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _Average():
            return Average(
                [_make_inner_metric_expression(o) for o in expression.operands],
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _Merge():
            return Merge(
                [_make_inner_metric_expression(o) for o in expression.operands],
                explicit_unit_id=explicit_unit_id,
                explicit_color=explicit_color,
            )
        case _:
            raise TypeError(expression)


def parse_expression(
    raw_expression: str | int | float,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> MetricExpression:
    if isinstance(raw_expression, (int, float)):
        return Constant(raw_expression)
    (
        stack,
        explicit_unit_id,
        explicit_color,
    ) = _parse_expression(raw_expression, translated_metrics)
    return _make_metric_expression(_resolve_stack(stack), explicit_unit_id, explicit_color)


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


def _make_conditional_metric_expression(
    expression: _MetricExpression | _ConditionalMetricExpression,
) -> ConditionalMetricExpression:
    match expression:
        case _GreaterThan():
            return GreaterThan(
                left=_make_metric_expression(expression.left, "", ""),
                right=_make_metric_expression(expression.right, "", ""),
            )
        case _GreaterEqualThan():
            return GreaterEqualThan(
                left=_make_metric_expression(expression.left, "", ""),
                right=_make_metric_expression(expression.right, "", ""),
            )
        case _LessThan():
            return LessThan(
                left=_make_metric_expression(expression.left, "", ""),
                right=_make_metric_expression(expression.right, "", ""),
            )
        case _LessEqualThan():
            return LessEqualThan(
                left=_make_metric_expression(expression.left, "", ""),
                right=_make_metric_expression(expression.right, "", ""),
            )
        case _:
            raise TypeError(expression)


def parse_conditional_expression(
    raw_expression: str,
    translated_metrics: Mapping[str, TranslatedMetric],
) -> ConditionalMetricExpression:
    (
        stack,
        _explicit_unit_id,
        _explicit_color,
    ) = _parse_expression(raw_expression, translated_metrics)
    return _make_conditional_metric_expression(_resolve_stack(stack))
