#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.graphing_engine._data._fetched import SeriesAttributes
from cmk.graphing_engine._data._timeseries import constant_time_series, TimeSeries

from ._operations import op_difference, op_fraction, op_product, op_sum, Operator
from ._quantity import EvaluatedQuantity, EvaluationContext, QuantityProtocol


def _operand_label_macros(operands: Sequence[EvaluatedQuantity]) -> Mapping[str, str]:
    # An operand may be a fan-out leaf that matched a single series, and then it carries that series'
    # title macros: the operation is the curve that gets drawn, so it has to carry them on.
    macros: dict[str, str] = {}
    for operand in operands:
        macros.update(operand.label_macros)
    return macros


def _operand_series_attributes(operands: Sequence[EvaluatedQuantity]) -> SeriesAttributes:
    # Same as the title macros: the operation is the drawn curve, so it carries on the attributes its
    # operands' series came with.
    attributes: dict[str, dict[str, str]] = {}
    for operand in operands:
        for kind, of_kind in operand.series_attributes.items():
            attributes.setdefault(kind, {}).update(of_kind)
    return attributes


def _apply_to_operands(
    operator: Operator,
    operands: Sequence[EvaluatedQuantity],
    context: EvaluationContext,
) -> EvaluatedQuantity:
    return EvaluatedQuantity(
        value=operator([operand.value for operand in operands]),
        time_series=TimeSeries(
            time_range=context.time_range,
            values=[
                operator(point)
                for point in itertools.zip_longest(
                    *(operand.time_series.values for operand in operands), fillvalue=None
                )
            ],
        ),
        label_macros=_operand_label_macros(operands),
        series_attributes=_operand_series_attributes(operands),
    )


def _collapse(results: Sequence[EvaluatedQuantity]) -> EvaluatedQuantity | None:
    # An operand of an operation must be single-valued: an absent operand is None; a fan-out operand
    # (a quantity that expands into several curves) cannot take part in an operation.
    match results:
        case []:
            return None
        case [single]:
            return single
        case _:
            raise ValueError("a fan-out quantity cannot be an operand of an operation")


def _collapse_operands(
    results: Sequence[Sequence[EvaluatedQuantity]],
) -> Sequence[EvaluatedQuantity] | None:
    # An operation is absent unless it has operands and every one of them is present: an empty
    # operation and any absent operand alike make the whole operation absent (value and series).
    operands = [_collapse(result) for result in results]
    present = [operand for operand in operands if operand is not None]
    if not operands or len(present) != len(operands):
        return None
    return present


def _operation_ident(kind: str, operands: Sequence[QuantityProtocol]) -> str:
    return f"{kind}({','.join(operand.ident() for operand in operands)})"


def _evaluate_operation(
    operator: Operator,
    operands: Sequence[QuantityProtocol],
    context: EvaluationContext,
) -> Sequence[EvaluatedQuantity]:
    if (collapsed := _collapse_operands([context.evaluate(o) for o in operands])) is None:
        return []
    return [_apply_to_operands(operator, collapsed, context)]


@dataclass(frozen=True)
class Constant:
    value: int | float

    def kind(self) -> str:
        return "constant"

    def ident(self) -> str:
        return f"{self.kind()}({self.value})"

    def children(self) -> Sequence[QuantityProtocol]:
        return ()

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return [
            EvaluatedQuantity(
                value=self.value, time_series=constant_time_series(self.value, context.time_range)
            )
        ]


@dataclass(frozen=True)
class Sum:
    summands: tuple[QuantityProtocol, ...]

    def kind(self) -> str:
        return "sum"

    def ident(self) -> str:
        return _operation_ident(self.kind(), self.summands)

    def children(self) -> Sequence[QuantityProtocol]:
        return self.summands

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return _evaluate_operation(op_sum, self.summands, context)


@dataclass(frozen=True)
class Product:
    factors: tuple[QuantityProtocol, ...]

    def kind(self) -> str:
        return "product"

    def ident(self) -> str:
        return _operation_ident(self.kind(), self.factors)

    def children(self) -> Sequence[QuantityProtocol]:
        return self.factors

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return _evaluate_operation(op_product, self.factors, context)


@dataclass(frozen=True, kw_only=True)
class Difference:
    minuend: QuantityProtocol
    subtrahend: QuantityProtocol

    def kind(self) -> str:
        return "difference"

    def ident(self) -> str:
        return _operation_ident(self.kind(), (self.minuend, self.subtrahend))

    def children(self) -> Sequence[QuantityProtocol]:
        return (self.minuend, self.subtrahend)

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return _evaluate_operation(op_difference, (self.minuend, self.subtrahend), context)


@dataclass(frozen=True, kw_only=True)
class Fraction:
    dividend: QuantityProtocol
    divisor: QuantityProtocol

    def kind(self) -> str:
        return "fraction"

    def ident(self) -> str:
        return _operation_ident(self.kind(), (self.dividend, self.divisor))

    def children(self) -> Sequence[QuantityProtocol]:
        return (self.dividend, self.divisor)

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return _evaluate_operation(op_fraction, (self.dividend, self.divisor), context)
