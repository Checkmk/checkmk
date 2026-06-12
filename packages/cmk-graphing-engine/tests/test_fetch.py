#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import (
    ConsolidationFunction,
    EvaluatedGraph,
    Graph,
    Line,
    MetricName,
    PerformanceData,
    PerformanceValue,
    Quantity,
    RRDMetric,
    RRDMetricWithCF,
    ServiceRef,
    TimeRange,
    TimeSeries,
    update_graph_data,
)


def _id(text: str) -> str:
    return text


def _service() -> ServiceRef:
    return ServiceRef(host_name="h", service_name="svc")


def _time_range() -> TimeRange:
    return TimeRange(start=0, end=60, step=10)


def _rrd_with_cf(
    name: str,
    consolidation_function: ConsolidationFunction = ConsolidationFunction.AVERAGE,
) -> RRDMetricWithCF:
    return RRDMetricWithCF(
        host_name="h",
        service_name="svc",
        metric_name=MetricName(name),
        consolidation_function=consolidation_function,
    )


def _source(name: str) -> RRDMetric:
    # The raw RRD column the engine reads (built from a metric's originals).
    return RRDMetric(host_name="h", service_name="svc", metric_name=MetricName(name))


def _line(quantity: Quantity) -> Line:
    return Line(quantity=quantity, inverse=False)


def _perf(name: str, *, value: float = 1.0) -> PerformanceValue:
    return PerformanceValue(metric_name=MetricName(name), value=value)


def _perf_data(*values: PerformanceValue) -> PerformanceData:
    return PerformanceData(check_command="check_mk-test", values=list(values))


def _ts(*values: float | None) -> TimeSeries:
    return TimeSeries(time_range=_time_range(), values=list(values))


class _FakeRRDSource:
    def __init__(
        self,
        *,
        performance_response: Mapping[ServiceRef, PerformanceData] | None = None,
        time_series_response: Mapping[RRDMetric, TimeSeries] | None = None,
    ) -> None:
        self._performance_response = performance_response or {}
        self._time_series_response = time_series_response or {}
        self.performance_data_calls: list[tuple[ServiceRef, ...]] = []
        self.time_series_calls: list[
            tuple[tuple[RRDMetric, ...], TimeRange, ConsolidationFunction]
        ] = []

    def fetch_performance_data(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, PerformanceData]:
        self.performance_data_calls.append(tuple(services))
        return self._performance_response

    def fetch_time_series(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDMetric, TimeSeries]:
        self.time_series_calls.append((tuple(rrd_metrics), time_range, consolidation_function))
        return {
            metric: self._time_series_response[metric]
            for metric in rrd_metrics
            if metric in self._time_series_response
        }


def _update(
    *graphs: Graph,
    rrd: _FakeRRDSource,
    consolidation_function: ConsolidationFunction = ConsolidationFunction.AVERAGE,
    translations: Sequence[translations_v1.Translation] | None = None,
) -> Sequence[EvaluatedGraph]:
    return update_graph_data(
        graphs=graphs,
        translations=translations or [],
        metrics={},
        localizer=_id,
        consolidation_function=consolidation_function,
        time_range=_time_range(),
        rrd=rrd,
    )


def test_empty_graphs_returns_empty_list() -> None:
    rrd = _FakeRRDSource()
    assert _update(rrd=rrd) == []
    assert rrd.time_series_calls == []


def test_fetches_performance_data_and_time_series() -> None:
    cpu_user = _rrd_with_cf("cpu_user")
    graph = Graph(name="cpu", title="CPU", lines=[_line(cpu_user)])
    series = _ts(1.0, 2.0, 3.0)
    rrd = _FakeRRDSource(
        performance_response={_service(): _perf_data(_perf("cpu_user", value=42.0))},
        time_series_response={_source("cpu_user"): series},
    )

    [evaluated] = _update(graph, rrd=rrd)

    [line] = evaluated.lines
    assert line.curve.value == 42.0
    assert line.curve.time_series == series
    assert rrd.performance_data_calls == [(_service(),)]


def test_returns_one_evaluated_graph_per_graph_in_order() -> None:
    x = _rrd_with_cf("x")
    y = _rrd_with_cf("y")
    graph_x = Graph(name="x", title="x", lines=[_line(x)])
    graph_y = Graph(name="y", title="y", lines=[_line(y)])
    rrd = _FakeRRDSource(
        performance_response={_service(): _perf_data(_perf("x", value=1.0), _perf("y", value=2.0))},
        time_series_response={_source("x"): _ts(1.0), _source("y"): _ts(2.0)},
    )

    results = _update(graph_x, graph_y, rrd=rrd)

    assert [[line.curve.value for line in graph.lines] for graph in results] == [[1.0], [2.0]]


def test_evaluates_lines_in_both_directions() -> None:
    in_ = _rrd_with_cf("if_in")
    out = _rrd_with_cf("if_out")
    graph = Graph(
        name="if",
        title="Interface",
        lines=[_line(out), Line(quantity=in_, inverse=True)],
    )
    rrd = _FakeRRDSource(
        performance_response={_service(): _perf_data(_perf("if_in"), _perf("if_out"))},
        time_series_response={_source("if_in"): _ts(1.0), _source("if_out"): _ts(2.0)},
    )

    [evaluated] = _update(graph, rrd=rrd)

    assert [(line.curve.time_series, line.inverse) for line in evaluated.lines] == [
        (_ts(2.0), False),
        (_ts(1.0), True),
    ]


def test_scales_the_series_by_the_translation_scale() -> None:
    temp = _rrd_with_cf("temp")
    graph = Graph(name="g", title="g", lines=[_line(temp)])
    rrd = _FakeRRDSource(
        performance_response={_service(): _perf_data(_perf("temp", value=10.0))},
        time_series_response={_source("temp"): _ts(10.0, 20.0)},
    )
    # A translation scale of 2.0 is applied to both the value and the fetched series.
    translations = [
        translations_v1.Translation(
            name="t",
            check_commands=[translations_v1.PassiveCheck("test")],
            translations={"temp": translations_v1.ScaleBy(2.0)},
        )
    ]

    [evaluated] = _update(graph, rrd=rrd, translations=translations)

    [line] = evaluated.lines
    assert line.curve.value == 20.0
    assert line.curve.time_series == _ts(20.0, 40.0)


def test_fetches_a_renamed_metric_by_its_raw_column() -> None:
    # The metric is named "temp" but its data comes from the raw column "temperature".
    temp = _rrd_with_cf("temp")
    graph = Graph(name="g", title="g", lines=[_line(temp)])
    rrd = _FakeRRDSource(
        performance_response={_service(): _perf_data(_perf("temperature", value=5.0))},
        time_series_response={_source("temperature"): _ts(5.0)},
    )
    translations = [
        translations_v1.Translation(
            name="t",
            check_commands=[translations_v1.PassiveCheck("test")],
            translations={"temperature": translations_v1.RenameTo("temp")},
        )
    ]

    [evaluated] = _update(graph, rrd=rrd, translations=translations)

    [line] = evaluated.lines
    assert line.curve.time_series == _ts(5.0)
    # The raw column is fetched, not the translated name.
    [(rrd_metrics, _tr, _cf)] = rrd.time_series_calls
    assert rrd_metrics == (_source("temperature"),)


def test_merges_a_metrics_originals_taking_the_first_present_value() -> None:
    metric = _rrd_with_cf("m")
    graph = Graph(name="g", title="g", lines=[_line(metric)])
    rrd = _FakeRRDSource(
        performance_response={_service(): _perf_data(_perf("a"), _perf("b"))},
        time_series_response={_source("a"): _ts(1.0, None, 3.0), _source("b"): _ts(None, 2.0, 4.0)},
    )
    # Both raw metrics translate to "m", so its data merges their originals.
    translations = [
        translations_v1.Translation(
            name="t",
            check_commands=[translations_v1.PassiveCheck("test")],
            translations={
                "a": translations_v1.RenameTo("m"),
                "b": translations_v1.RenameTo("m"),
            },
        )
    ]

    [evaluated] = _update(graph, rrd=rrd, translations=translations)

    # Per point, the first present value wins: a where it has data, otherwise b.
    [line] = evaluated.lines
    assert line.curve.time_series == _ts(1.0, 2.0, 3.0)


def test_aligns_a_natively_gridded_series_to_the_requested_range() -> None:
    metric = _rrd_with_cf("m")
    graph = Graph(name="g", title="g", lines=[_line(metric)])
    # The backend returns the series on its own finer grid (12 five-second points); the engine
    # downsamples it onto the requested 10-second grid (six points) before evaluating.
    native = TimeSeries(
        time_range=TimeRange(start=0, end=60, step=5),
        values=[float(value) for value in range(1, 13)],
    )
    rrd = _FakeRRDSource(
        performance_response={_service(): _perf_data(_perf("m"))},
        time_series_response={_source("m"): native},
    )

    [evaluated] = _update(graph, rrd=rrd)

    [line] = evaluated.lines
    assert line.curve.time_series.time_range == _time_range()
    assert len(line.curve.time_series.values) == 6


def test_fetches_one_batch_per_consolidation_function() -> None:
    avg_metric = _rrd_with_cf("a", ConsolidationFunction.AVERAGE)
    max_metric = _rrd_with_cf("b", ConsolidationFunction.MAX)
    graph = Graph(name="g", title="g", lines=[_line(avg_metric), _line(max_metric)])
    rrd = _FakeRRDSource(
        performance_response={_service(): _perf_data(_perf("a"), _perf("b"))},
        time_series_response={_source("a"): _ts(1.0), _source("b"): _ts(2.0)},
    )

    _update(graph, rrd=rrd)

    columns_by_cf = {cf: rrd_metrics for rrd_metrics, _tr, cf in rrd.time_series_calls}
    assert columns_by_cf == {
        ConsolidationFunction.AVERAGE: (_source("a"),),
        ConsolidationFunction.MAX: (_source("b"),),
    }


def test_bare_metric_uses_the_fallback_consolidation_function() -> None:
    # A bare RRDMetric uses the fallback function; a pinned RRDMetricWithCF keeps its own.
    bare = RRDMetric(host_name="h", service_name="svc", metric_name=MetricName("load"))
    pinned = _rrd_with_cf("peak", ConsolidationFunction.MAX)
    graph = Graph(name="g", title="g", lines=[_line(bare), _line(pinned)])
    rrd = _FakeRRDSource(
        performance_response={_service(): _perf_data(_perf("load"), _perf("peak"))},
        time_series_response={_source("load"): _ts(1.0), _source("peak"): _ts(2.0)},
    )

    _update(graph, rrd=rrd, consolidation_function=ConsolidationFunction.AVERAGE)

    columns_by_cf = {cf: rrd_metrics for rrd_metrics, _tr, cf in rrd.time_series_calls}
    assert columns_by_cf == {
        ConsolidationFunction.AVERAGE: (_source("load"),),
        ConsolidationFunction.MAX: (_source("peak"),),
    }
