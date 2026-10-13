#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing_engine import (
    AutoPrecision,
    ConsolidationFunction,
    constant_time_series,
    Curve,
    CurveAttributes,
    DecimalNotation,
    evaluate_graphs,
    EvaluatedGraph,
    EvaluatedQuantity,
    EvaluationContext,
    FetchedData,
    Graph,
    HostName,
    Line,
    MetricName,
    PerformanceData,
    QuantityProtocol,
    RRDMetric,
    ServiceName,
    TimeRange,
    TimeSeries,
    Unit,
)

from ._fixtures import _FakeRRDFetchData

_UNIT = Unit(notation=DecimalNotation(""), precision=AutoPrecision(2))


_STEP = 10


def _time_range() -> TimeRange:
    return TimeRange(start=0, end=60, step=_STEP)


def _rrd(name: str) -> RRDMetric:
    return RRDMetric(
        host_name=HostName("h"),
        service_name=ServiceName("svc"),
        metric_name=MetricName(name),
        consolidation_function=ConsolidationFunction.AVERAGE,
    )


def _curve(quantity: QuantityProtocol) -> Curve:
    return Curve(quantity=quantity, attributes=CurveAttributes(title="t", unit=_UNIT, color="#000"))


def _line(quantity: QuantityProtocol, *, inverse: bool = False) -> Line:
    return Line(curve=_curve(quantity), inverse=inverse)


def _ts(*values: float | None) -> TimeSeries:
    return TimeSeries(
        time_range=TimeRange(start=0, end=_STEP * len(values), step=_STEP), values=list(values)
    )


def _perf(value: float | None, **thresholds: float | None) -> PerformanceData:
    return PerformanceData(value=value, **thresholds)


def _fetched(value: float | None, series: TimeSeries | None) -> Sequence[FetchedData]:
    return [FetchedData(performance_data=_perf(value), time_series=series)]


def _update(
    *graphs: Graph,
    fetch_data: _FakeRRDFetchData,
    consolidation_function: ConsolidationFunction = ConsolidationFunction.AVERAGE,
) -> Sequence[EvaluatedGraph]:
    return evaluate_graphs(
        consolidation_function=consolidation_function,
        time_range=_time_range(),
        graphs=graphs,
        fetch_data=fetch_data,
    )


def test_empty_graphs_returns_empty_list() -> None:
    assert _update(fetch_data=_FakeRRDFetchData()) == []


def test_fetches_performance_data_and_time_series() -> None:
    cpu_user = _rrd("cpu_user")
    graph = Graph(name="cpu", title="CPU", kind="test", lines=[_line(cpu_user)])
    series = _ts(1.0, 2.0, 3.0)
    fetch_data = _FakeRRDFetchData({cpu_user: _fetched(42.0, series)})

    [evaluated] = _update(graph, fetch_data=fetch_data)

    [line] = evaluated.lines
    assert line.curve.value == 42.0
    assert line.curve.time_series == series


def test_returns_one_evaluated_graph_per_graph_in_order() -> None:
    x, y = _rrd("x"), _rrd("y")
    graph_x = Graph(name="x", title="x", kind="test", lines=[_line(x)])
    graph_y = Graph(name="y", title="y", kind="test", lines=[_line(y)])
    fetch_data = _FakeRRDFetchData({x: _fetched(1.0, _ts(1.0)), y: _fetched(2.0, _ts(2.0))})

    results = _update(graph_x, graph_y, fetch_data=fetch_data)

    assert [[line.curve.value for line in graph.lines] for graph in results] == [[1.0], [2.0]]


def test_reports_the_time_range_the_fetched_series_sit_on() -> None:
    cpu_user = _rrd("cpu_user")
    graph = Graph(name="cpu", title="CPU", kind="test", lines=[_line(cpu_user)])
    served = TimeRange(start=0, end=120, step=60)
    series = TimeSeries(time_range=served, values=[1.0, 2.0])
    fetch_data = _FakeRRDFetchData({cpu_user: _fetched(42.0, series)})

    [evaluated] = _update(graph, fetch_data=fetch_data)

    assert evaluated.time_range == served


_AHEAD = 600


@dataclass(frozen=True)
class _BeyondTheFetch:
    def kind(self) -> str:
        return "beyond_the_fetch"

    def ident(self) -> str:
        return self.kind()

    def children(self) -> Sequence[QuantityProtocol]:
        return ()

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        fetched = context.time_range
        ahead = TimeRange(start=fetched.end, end=fetched.end + _AHEAD, step=fetched.step)
        return [EvaluatedQuantity(value=None, time_series=constant_time_series(1.0, ahead))]

    def attributes(
        self,
        _localizer: Callable[[str], str],
        _registered_metrics: Mapping[str, metrics_v1.Metric],
        /,
    ) -> CurveAttributes | None:
        return None


def test_reports_the_time_range_of_curves_computed_beyond_the_fetch() -> None:
    graph = Graph(name="forecast", title="Forecast", kind="test", lines=[_line(_BeyondTheFetch())])

    [evaluated] = _update(graph, fetch_data=_FakeRRDFetchData())

    assert evaluated.time_range == TimeRange(start=60, end=660, step=10)


def test_reports_the_requested_time_range_without_fetched_series() -> None:
    graph = Graph(name="empty", title="Empty", kind="test")

    [evaluated] = _update(graph, fetch_data=_FakeRRDFetchData())

    assert evaluated.time_range == _time_range()


def _fetched_on_the_grid_of_the_first(values: Sequence[float | None]) -> TimeSeries:
    x, y = _rrd("x"), _rrd("y")
    graph = Graph(name="g", title="g", kind="test", lines=[_line(x), _line(y)])
    grid = _ts(1.0, 2.0, 3.0).time_range
    fetch_data = _FakeRRDFetchData(
        {
            x: _fetched(3.0, _ts(1.0, 2.0, 3.0)),
            y: _fetched(None, TimeSeries(time_range=grid, values=list(values))),
        }
    )

    [evaluated] = _update(graph, fetch_data=fetch_data)

    return evaluated.lines[1].curve.time_series


def test_a_series_short_of_the_grid_is_padded_with_gaps() -> None:
    assert _fetched_on_the_grid_of_the_first([4.0, 5.0]).values == [4.0, 5.0, None]


def test_a_series_beyond_the_grid_is_cut_at_its_end() -> None:
    assert _fetched_on_the_grid_of_the_first([4.0, 5.0, 6.0, 7.0]).values == [4.0, 5.0, 6.0]


def test_evaluates_lines_in_both_directions() -> None:
    in_, out = _rrd("if_in"), _rrd("if_out")
    graph = Graph(
        name="if",
        title="Interface",
        kind="test",
        lines=[_line(out), _line(in_, inverse=True)],
    )
    fetch_data = _FakeRRDFetchData({in_: _fetched(1.0, _ts(1.0)), out: _fetched(2.0, _ts(2.0))})

    [evaluated] = _update(graph, fetch_data=fetch_data)

    assert [(line.curve.time_series, line.inverse) for line in evaluated.lines] == [
        (_ts(2.0), False),
        (_ts(1.0), True),
    ]


def test_resolves_a_title_expression_against_a_non_drawn_metric() -> None:
    # The title references "cores", which is not drawn; it still resolves against the service's
    # (source-delivered) performance data.
    load = _rrd("load")
    cores = RRDMetric(
        host_name=HostName("h"), service_name=ServiceName("svc"), metric_name=MetricName("cores")
    )
    graph = Graph(
        name="g",
        title='Load - _EXPRESSION:{"metric": "cores", "scalar": "max"} cores',
        kind="test",
        lines=[_line(load)],
    )
    fetch_data = _FakeRRDFetchData(
        {
            load: _fetched(1.0, _ts(1.0)),
            cores: [FetchedData(performance_data=_perf(4.0, maximum=8.0), time_series=None)],
        }
    )

    [evaluated] = _update(graph, fetch_data=fetch_data)

    assert evaluated.title == "Load - 8 cores"
