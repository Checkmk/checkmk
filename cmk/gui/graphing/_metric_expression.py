#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, KW_ONLY
from typing import Literal

from cmk.utils.metrics import MetricName
from cmk.utils.resulttype import Error, OK, Result

from cmk.gui.i18n import _, translate_to_current_language

from cmk.graphing.v1 import metrics as metrics_api

from ._color import mix_colors, parse_color, parse_color_from_api, render_color, scalar_colors
from ._formatter import AutoPrecision, StrictPrecision
from ._from_api import parse_unit_from_api
from ._legacy import get_unit_info, unit_info, UnitInfo
from ._metric_operation import GraphConsolidationFunction, line_type_mirror, LineType
from ._metrics import get_metric_spec
from ._translated_metrics import TranslatedMetric
from ._unit import ConvertibleUnitSpecification, DecimalNotation

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
class BaseEvaluated:
    value: int | float
    unit_spec: ConvertibleUnitSpecification | UnitInfo
    color: str


@dataclass(frozen=True)
class EvaluationError:
    reason: str
    metric_name: str = ""


@dataclass(frozen=True)
class ScalarName:
    metric_name: str
    scalar_name: Literal["warn", "crit", "min", "max"]


class BaseMetricExpression(abc.ABC):
    @abc.abstractmethod
    def ident(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
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

    def ident(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        return OK(
            BaseEvaluated(
                self.value,
                (
                    _FALLBACK_UNIT_SPEC_INT
                    if isinstance(self.value, int)
                    else _FALLBACK_UNIT_SPEC_FLOAT
                ),
                "#000000",
            )
        )

    def metric_names(self) -> Iterator[str]:
        yield from ()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from ()


@dataclass(frozen=True)
class Metric(BaseMetricExpression):
    name: MetricName
    consolidation: GraphConsolidationFunction | None = None

    def ident(self) -> str:
        return f"{self.__class__.__name__}({self.name},{self.consolidation})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if not (translated_metric := translated_metrics.get(self.name)):
            return Error(EvaluationError(f"No such translated metric of {self.name!r}", self.name))
        return OK(
            BaseEvaluated(
                translated_metric.value,
                translated_metric.unit_spec,
                translated_metric.color,
            )
        )

    def metric_names(self) -> Iterator[str]:
        yield self.name

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from ()


@dataclass(frozen=True)
class WarningOf(BaseMetricExpression):
    metric: Metric

    def ident(self) -> str:
        return f"{self.__class__.__name__}({self.metric.ident()})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if not (translated_metric := translated_metrics.get(self.metric.name)):
            return Error(
                EvaluationError(
                    f"No such translated metric of {self.metric.name!r}",
                    self.metric.name,
                )
            )

        if (warn_value := translated_metric.scalar.get("warn")) is None:
            return Error(
                EvaluationError(f"No such warning value of {self.metric.name!r}", self.metric.name)
            )

        if (result := self.metric.evaluate(translated_metrics)).is_error():
            return result

        return OK(BaseEvaluated(warn_value, result.ok.unit_spec, scalar_colors["warn"]))

    def metric_names(self) -> Iterator[str]:
        yield from self.metric.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield ScalarName(self.metric.name, "warn")


@dataclass(frozen=True)
class CriticalOf(BaseMetricExpression):
    metric: Metric

    def ident(self) -> str:
        return f"{self.__class__.__name__}({self.metric.ident()})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if not (translated_metric := translated_metrics.get(self.metric.name)):
            return Error(
                EvaluationError(
                    f"No such translated metric of {self.metric.name!r}",
                    self.metric.name,
                )
            )

        if (crit_value := translated_metric.scalar.get("crit")) is None:
            return Error(
                EvaluationError(f"No such critical value of {self.metric.name!r}", self.metric.name)
            )

        if (result := self.metric.evaluate(translated_metrics)).is_error():
            return result

        return OK(BaseEvaluated(crit_value, result.ok.unit_spec, scalar_colors["crit"]))

    def metric_names(self) -> Iterator[str]:
        yield from self.metric.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield ScalarName(self.metric.name, "crit")


@dataclass(frozen=True)
class MinimumOf(BaseMetricExpression):
    metric: Metric

    def ident(self) -> str:
        return f"{self.__class__.__name__}({self.metric.ident()})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if not (translated_metric := translated_metrics.get(self.metric.name)):
            return Error(
                EvaluationError(
                    f"No such translated metric of {self.metric.name!r}",
                    self.metric.name,
                )
            )

        if (min_value := translated_metric.scalar.get("min")) is None:
            return Error(
                EvaluationError(f"No such minimum value of {self.metric.name!r}", self.metric.name)
            )

        if (result := self.metric.evaluate(translated_metrics)).is_error():
            return result

        return OK(BaseEvaluated(min_value, result.ok.unit_spec, "#808080"))

    def metric_names(self) -> Iterator[str]:
        yield from self.metric.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield ScalarName(self.metric.name, "min")


@dataclass(frozen=True)
class MaximumOf(BaseMetricExpression):
    metric: Metric

    def ident(self) -> str:
        return f"{self.__class__.__name__}({self.metric.ident()})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if not (translated_metric := translated_metrics.get(self.metric.name)):
            return Error(
                EvaluationError(
                    f"No such translated metric of {self.metric.name!r}",
                    self.metric.name,
                )
            )

        if (max_value := translated_metric.scalar.get("max")) is None:
            return Error(
                EvaluationError(f"No such maximum value of {self.metric.name!r}", self.metric.name)
            )

        if (result := self.metric.evaluate(translated_metrics)).is_error():
            return result

        return OK(BaseEvaluated(max_value, result.ok.unit_spec, "#808080"))

    def metric_names(self) -> Iterator[str]:
        yield from self.metric.metric_names()

    def scalar_names(self) -> Iterator[ScalarName]:
        yield ScalarName(self.metric.name, "max")


@dataclass(frozen=True)
class Sum(BaseMetricExpression):
    summands: Sequence[BaseMetricExpression]

    def ident(self) -> str:
        return f"{self.__class__.__name__}({','.join(s.ident() for s in self.summands)})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if len(self.summands) == 0:
            return Error(EvaluationError("No summands given"))

        if (first_result := self.summands[0].evaluate(translated_metrics)).is_error():
            return first_result

        values = [first_result.ok.value]
        unit_spec = first_result.ok.unit_spec
        color = first_result.ok.color
        for successor in self.summands[1:]:
            if (successor_result := successor.evaluate(translated_metrics)).is_error():
                return successor_result

            values.append(successor_result.ok.value)
            unit_spec = _unit_add(unit_spec, successor_result.ok.unit_spec)
            color = _choose_operator_color(color, successor_result.ok.color)

        return OK(BaseEvaluated(sum(values), unit_spec, color))

    def metric_names(self) -> Iterator[str]:
        yield from (n for s in self.summands for n in s.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for s in self.summands for n in s.scalar_names())


@dataclass(frozen=True)
class Product(BaseMetricExpression):
    factors: Sequence[BaseMetricExpression]

    def ident(self) -> str:
        return f"{self.__class__.__name__}({','.join(f.ident() for f in self.factors)})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if len(self.factors) == 0:
            return Error(EvaluationError("No factors given"))

        if (first_result := self.factors[0].evaluate(translated_metrics)).is_error():
            return first_result

        product = first_result.ok.value
        unit_spec = first_result.ok.unit_spec
        color = first_result.ok.color
        for successor in self.factors[1:]:
            if (successor_result := successor.evaluate(translated_metrics)).is_error():
                return successor_result

            product *= successor_result.ok.value
            unit_spec = _unit_mult(unit_spec, successor_result.ok.unit_spec)
            color = _choose_operator_color(color, successor_result.ok.color)

        return OK(BaseEvaluated(product, unit_spec, color))

    def metric_names(self) -> Iterator[str]:
        yield from (n for f in self.factors for n in f.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for f in self.factors for n in f.scalar_names())


@dataclass(frozen=True, kw_only=True)
class Difference(BaseMetricExpression):
    minuend: BaseMetricExpression
    subtrahend: BaseMetricExpression

    def ident(self) -> str:
        return f"{self.__class__.__name__}({self.minuend.ident()},{self.subtrahend.ident()})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if (minuend_result := self.minuend.evaluate(translated_metrics)).is_error():
            return minuend_result

        if (subtrahend_result := self.subtrahend.evaluate(translated_metrics)).is_error():
            return subtrahend_result

        return OK(
            BaseEvaluated(
                (
                    0.0
                    if subtrahend_result.ok.value == 0.0
                    else minuend_result.ok.value - subtrahend_result.ok.value
                ),
                _unit_sub(minuend_result.ok.unit_spec, subtrahend_result.ok.unit_spec),
                _choose_operator_color(minuend_result.ok.color, subtrahend_result.ok.color),
            )
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

    def ident(self) -> str:
        return f"{self.__class__.__name__}({self.dividend.ident()},{self.divisor.ident()})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if (dividend_result := self.dividend.evaluate(translated_metrics)).is_error():
            return dividend_result

        if (divisor_result := self.divisor.evaluate(translated_metrics)).is_error():
            return divisor_result

        return OK(
            BaseEvaluated(
                (
                    0.0
                    if divisor_result.ok.value == 0.0
                    else dividend_result.ok.value / divisor_result.ok.value
                ),
                _unit_div(dividend_result.ok.unit_spec, divisor_result.ok.unit_spec),
                _choose_operator_color(dividend_result.ok.color, divisor_result.ok.color),
            )
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

    def ident(self) -> str:
        return f"{self.__class__.__name__}({','.join(o.ident() for o in self.operands)})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if len(self.operands) == 0:
            return Error(EvaluationError("No operands given"))

        if (minimum_result := self.operands[0].evaluate(translated_metrics)).is_error():
            return minimum_result

        for operand in self.operands[1:]:
            if (operand_result := operand.evaluate(translated_metrics)).is_error():
                return operand_result

            if operand_result.ok.value < minimum_result.ok.value:
                minimum_result = operand_result

        return minimum_result

    def metric_names(self) -> Iterator[str]:
        yield from (n for o in self.operands for n in o.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for o in self.operands for n in o.scalar_names())


@dataclass(frozen=True)
class Maximum(BaseMetricExpression):
    operands: Sequence[BaseMetricExpression]

    def ident(self) -> str:
        return f"{self.__class__.__name__}({','.join(o.ident() for o in self.operands)})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if len(self.operands) == 0:
            return Error(EvaluationError("No operands given"))

        if (maximum_result := self.operands[0].evaluate(translated_metrics)).is_error():
            return maximum_result

        for operand in self.operands[1:]:
            if (operand_result := operand.evaluate(translated_metrics)).is_error():
                return operand_result

            if operand_result.ok.value > maximum_result.ok.value:
                maximum_result = operand_result

        return maximum_result

    def metric_names(self) -> Iterator[str]:
        yield from (n for o in self.operands for n in o.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for o in self.operands for n in o.scalar_names())


# Special metric declarations for custom graphs


@dataclass(frozen=True)
class Average(BaseMetricExpression):
    operands: Sequence[BaseMetricExpression]

    def ident(self) -> str:
        return f"{self.__class__.__name__}({','.join(o.ident() for o in self.operands)})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if len(self.operands) == 0:
            return Error(EvaluationError("No operands given"))

        if (result := Sum(self.operands).evaluate(translated_metrics)).is_error():
            return result

        return OK(
            BaseEvaluated(
                result.ok.value / len(self.operands),
                result.ok.unit_spec,
                result.ok.color,
            )
        )

    def metric_names(self) -> Iterator[str]:
        yield from (n for o in self.operands for n in o.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for o in self.operands for n in o.scalar_names())


@dataclass(frozen=True)
class Merge(BaseMetricExpression):
    operands: Sequence[BaseMetricExpression]

    def ident(self) -> str:
        return f"{self.__class__.__name__}({','.join(o.ident() for o in self.operands)})"

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[BaseEvaluated, EvaluationError]:
        if len(self.operands) == 0:
            return Error(EvaluationError("No operands given"))

        for operand in self.operands:
            if (result := operand.evaluate(translated_metrics)).is_error():
                return result

            if result.value is not None:
                return result

        return Error(EvaluationError("Unable to evaluate operands"))

    def metric_names(self) -> Iterator[str]:
        yield from (n for o in self.operands for n in o.metric_names())

    def scalar_names(self) -> Iterator[ScalarName]:
        yield from (n for o in self.operands for n in o.scalar_names())


@dataclass(frozen=True)
class Evaluated:
    base: BaseMetricExpression
    value: int | float
    unit_spec: ConvertibleUnitSpecification | UnitInfo
    color: str
    line_type: LineType
    title: str

    def ident(self) -> str:
        return self.base.ident()

    def metric_names(self) -> Iterator[str]:
        yield from self.base.metric_names()

    def mirror(self) -> Evaluated:
        return Evaluated(
            self.base,
            self.value,
            self.unit_spec,
            self.color,
            line_type_mirror(self.line_type),
            self.title,
        )


@dataclass(frozen=True)
class MetricExpression:
    base: BaseMetricExpression
    _: KW_ONLY
    unit_spec: ConvertibleUnitSpecification | str | None = None
    color: str = ""
    line_type: LineType
    title: str = ""

    def ident(self) -> str:
        return self.base.ident()

    def evaluate(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
    ) -> Result[Evaluated, EvaluationError]:
        if (result := self.base.evaluate(translated_metrics)).is_error():
            return Error(result.error)

        def _title() -> str:
            if self.title:
                return self.title
            if metric_names := list(self.base.metric_names()):
                return translated_metrics[metric_names[0]].title
            return ""

        return OK(
            Evaluated(
                self.base,
                result.ok.value,
                (
                    get_unit_info(self.unit_spec)
                    if isinstance(self.unit_spec, str)
                    else (self.unit_spec or result.ok.unit_spec)
                ),
                self.color or result.ok.color,
                self.line_type,
                _title(),
            )
        )

    def mirror(self) -> MetricExpression:
        return MetricExpression(
            self.base,
            unit_spec=self.unit_spec,
            color=self.color,
            line_type=line_type_mirror(self.line_type),
            title=self.title,
        )


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
                unit_spec=parse_unit_from_api(quantity.unit),
                color=parse_color_from_api(quantity.color),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
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
                color=parse_color_from_api(quantity.color),
                line_type=line_type,
                title=_("Minimum of %s") % get_metric_spec(quantity.metric_name).title,
            )
        case metrics_api.MaximumOf():
            return MetricExpression(
                MaximumOf(Metric(quantity.metric_name)),
                color=parse_color_from_api(quantity.color),
                line_type=line_type,
                title=_("Maximum of %s") % get_metric_spec(quantity.metric_name).title,
            )
        case metrics_api.Sum():
            return MetricExpression(
                Sum([parse_base_expression_from_api(s) for s in quantity.summands]),
                color=parse_color_from_api(quantity.color),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
            )
        case metrics_api.Product():
            return MetricExpression(
                Product([parse_base_expression_from_api(f) for f in quantity.factors]),
                unit_spec=parse_unit_from_api(quantity.unit),
                color=parse_color_from_api(quantity.color),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
            )
        case metrics_api.Difference():
            return MetricExpression(
                Difference(
                    minuend=parse_base_expression_from_api(quantity.minuend),
                    subtrahend=parse_base_expression_from_api(quantity.subtrahend),
                ),
                color=parse_color_from_api(quantity.color),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
            )
        case metrics_api.Fraction():
            return MetricExpression(
                Fraction(
                    dividend=parse_base_expression_from_api(quantity.dividend),
                    divisor=parse_base_expression_from_api(quantity.divisor),
                ),
                unit_spec=parse_unit_from_api(quantity.unit),
                color=parse_color_from_api(quantity.color),
                line_type=line_type,
                title=str(quantity.title.localize(translate_to_current_language)),
            )
