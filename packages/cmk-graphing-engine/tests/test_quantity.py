#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The open quantity protocol: a custom quantity kind defined entirely outside the engine
is evaluated by the engine without any change to its code."""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass

import pytest

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing_engine import (
    AutoPrecision,
    Curve,
    CurveAttributes,
    DecimalNotation,
    EvaluatedCurve,
    EvaluatedQuantity,
    EvaluationContext,
    FetchedData,
    Graph,
    HostName,
    Line,
    MetricName,
    MetricProtocol,
    PerformanceData,
    QuantityProtocol,
    RRDMetric,
    ServiceName,
    Sum,
    TimeRange,
    TimeSeries,
    Unit,
)
from cmk.graphing_engine._graph_evaluate import _evaluate_graph

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))
_TR = TimeRange(start=0, end=30, step=10)  # three data points


def _metric(name: str) -> RRDMetric:
    return RRDMetric(
        host_name=HostName("h"), service_name=ServiceName("svc"), metric_name=MetricName(name)
    )


def _data(*, value: float | None) -> PerformanceData:
    return PerformanceData(value=value)


@dataclass(frozen=True)
class Negated:
    """A custom quantity, unknown to the engine, that flips the sign of another quantity."""

    operand: QuantityProtocol

    def kind(self) -> str:
        return "negated"

    def ident(self) -> str:
        return f"negated({self.operand.ident()})"

    def metrics(self) -> Iterable[MetricProtocol]:
        yield from self.operand.metrics()

    def attributes(
        self,
        localizer: Callable[[str], str],
        registered_metrics: Mapping[str, metrics_v1.Metric],
    ) -> CurveAttributes | None:
        return self.operand.attributes(localizer, registered_metrics)

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return [
            EvaluatedQuantity(
                value=None if evaluated.value is None else -evaluated.value,
                time_series=TimeSeries(
                    time_range=context.time_range,
                    values=[None if v is None else -v for v in evaluated.time_series.values],
                ),
                label_macros=evaluated.label_macros,
            )
            for evaluated in self.operand.evaluate(context)
        ]


@dataclass(frozen=True)
class _FanOut:
    """A custom quantity that expands into one labelled curve per given label."""

    labels: Sequence[str]

    def kind(self) -> str:
        return "fan_out"

    def ident(self) -> str:
        return "fan_out"

    def metrics(self) -> Iterable[MetricProtocol]:
        return ()

    def attributes(
        self,
        _localizer: Callable[[str], str],
        _registered_metrics: Mapping[str, metrics_v1.Metric],
    ) -> CurveAttributes | None:
        return None

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        return [
            EvaluatedQuantity(
                value=float(index),
                time_series=TimeSeries(time_range=context.time_range, values=[float(index)] * 3),
                label_macros={"$SERIES_ID$": label},
            )
            for index, label in enumerate(self.labels)
        ]


def test_engine_fans_out_a_quantity_into_labelled_curves() -> None:
    attributes = CurveAttributes(title="q", unit=_UNIT, color="#000000")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        lines=[
            Line(
                curve=Curve(quantity=_FanOut(labels=["a", "b"]), attributes=attributes),
                inverse=False,
            )
        ],
    )
    result = _evaluate_graph(graph, EvaluationContext(time_range=_TR))
    # One line per fanned series: distinct ids and colours, and the per-series label folded into the
    # base title.
    assert [line.curve.id for line in result.lines] == ["fan_out", "fan_out#2"]
    assert [line.curve.attributes.title for line in result.lines] == ["q - a", "q - b"]
    assert result.lines[0].curve.attributes.color != result.lines[1].curve.attributes.color


def test_engine_rejects_a_fan_out_quantity_as_an_operation_operand() -> None:
    # A fan-out quantity has no single value to feed an operation, so using it as an operand is an
    # error rather than a silent collapse.
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        lines=[
            Line(
                curve=Curve(
                    quantity=Sum(summands=[_FanOut(labels=["a", "b"])]),
                    attributes=CurveAttributes(title="s", unit=_UNIT, color="#000000"),
                ),
                inverse=False,
            )
        ],
    )
    with pytest.raises(ValueError, match="fan-out"):
        _evaluate_graph(graph, EvaluationContext(time_range=_TR))


def test_custom_quantity_is_accepted_as_a_quantity() -> None:
    # Static structural conformance: a Negated is usable wherever a QuantityProtocol is expected.
    a = _metric("a")
    quantity: QuantityProtocol = Negated(operand=a)
    assert list(quantity.metrics()) == [a]


def test_engine_evaluates_a_custom_quantity_without_engine_changes() -> None:
    a = _metric("a")
    attributes = CurveAttributes(title="neg a", unit=_UNIT, color="#000000")
    graph = Graph(
        name="g",
        title="g",
        kind="test",
        lines=[
            Line(curve=Curve(quantity=Negated(operand=a), attributes=attributes), inverse=False)
        ],
    )
    result = _evaluate_graph(
        graph,
        EvaluationContext(
            time_range=_TR,
            fetched={
                a: [
                    FetchedData(
                        performance_data=_data(value=3.0),
                        time_series=TimeSeries(time_range=_TR, values=[1.0, None, 3.0]),
                    )
                ]
            },
        ),
    )
    assert result.lines[0].curve == EvaluatedCurve(
        id="negated(rrd_metric(h/svc/a))",
        attributes=attributes,
        value=-3.0,
        time_series=TimeSeries(time_range=_TR, values=[-1.0, None, -3.0]),
    )


def test_a_metric_leaf_is_a_quantity() -> None:
    # A metric is the leaf the fetch resolves data for *and* the quantity that draws it, so anything
    # a graph can ask to fetch can also be evaluated - which is what the codec relies on when it
    # serializes the metric of a threshold.
    def _as_quantity(quantity: QuantityProtocol) -> QuantityProtocol:
        return quantity

    def _as_metric(metric: MetricProtocol) -> MetricProtocol:
        return metric

    metric = _metric("a")
    assert _as_quantity(_as_metric(metric)) is metric
