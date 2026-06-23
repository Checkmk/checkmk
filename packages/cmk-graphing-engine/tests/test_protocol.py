#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The open quantity protocol: a custom quantity kind defined entirely outside the engine
is evaluated by the engine without any change to its code."""

from collections.abc import Iterable
from dataclasses import dataclass

from cmk.graphing_engine import (
    AutoPrecision,
    DecimalNotation,
    EvaluatedCurve,
    Graph,
    Line,
    MetricName,
    RRDMetric,
    TimeRange,
    TimeSeries,
    Unit,
)
from cmk.graphing_engine._evaluate import evaluate_graph
from cmk.graphing_engine._objects import (
    DisplayAttributes,
    EvaluationContext,
    Quantity,
    RRDMetricData,
)

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))
_TR = TimeRange(start=0, end=30, step=10)  # three data points


def _metric(name: str) -> RRDMetric:
    return RRDMetric(host_name="h", service_name="svc", metric_name=MetricName(name))


def _data(name: str, *, value: float | None) -> RRDMetricData:
    return RRDMetricData(value=value, originals=[], title=name, unit=_UNIT, color="#28a2f3")


@dataclass(frozen=True)
class Negated:
    """A custom quantity, unknown to the engine, that flips the sign of another quantity."""

    title: str
    color: str
    operand: Quantity

    def rrd_metrics(self) -> Iterable[RRDMetric]:
        yield from self.operand.rrd_metrics()

    def evaluate_value(self, context: EvaluationContext) -> float | None:
        value = self.operand.evaluate_value(context)
        return None if value is None else -value

    def evaluate_time_series(self, context: EvaluationContext) -> TimeSeries:
        evaluated = self.operand.evaluate_time_series(context)
        return TimeSeries(
            time_range=context.time_range,
            values=[None if v is None else -v for v in evaluated.values],
        )

    def evaluate_attributes(self, context: EvaluationContext) -> DisplayAttributes | None:
        operand = self.operand.evaluate_attributes(context)
        return (
            None
            if operand is None
            else DisplayAttributes(title=self.title, unit=operand.unit, color=self.color)
        )


def test_custom_quantity_is_accepted_as_a_quantity() -> None:
    # Static structural conformance: a Negated is usable wherever a Quantity is expected.
    a = _metric("a")
    quantity: Quantity = Negated(title="neg", color="#000000", operand=a)
    assert list(quantity.rrd_metrics()) == [a]


def test_engine_evaluates_a_custom_quantity_without_engine_changes() -> None:
    a = _metric("a")
    graph = Graph(
        name="g",
        title="g",
        lines=[Line(quantity=Negated(title="neg a", color="#000000", operand=a), inverse=False)],
    )
    result = evaluate_graph(
        graph,
        {a: _data("a", value=3.0)},
        {a: TimeSeries(time_range=_TR, values=[1.0, None, 3.0])},
        {},
        _TR,
    )
    assert result.lines[0].curve == EvaluatedCurve(
        title="neg a",
        unit=_UNIT,
        color="#000000",
        value=-3.0,
        time_series=TimeSeries(time_range=_TR, values=[-1.0, None, -3.0]),
    )
