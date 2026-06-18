#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""End-to-end tests of the discover -> update lifecycle, exercising both entry points together.

The central invariant: refreshing a discovered graph through update_graph_data reproduces exactly
what discovery rendered (title, vertical range, stacks and lines), because both go through the same
evaluation against the same data. Each test fakes a different shape of performance / time series
data to cover that invariant from several angles.
"""

from collections.abc import Mapping, Sequence

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import (
    build_graphs,
    ConsolidationFunction,
    DiscoveredGraph,
    evaluate_graphs,
    EvaluatedGraph,
    fetch_translated_metrics,
    MetricName,
    PerformanceData,
    PerformanceValue,
    RRDMetric,
    ServiceRef,
    TimeRange,
    TimeSeries,
    update_graph_data,
)

_SERVICE = ServiceRef(host_name="h", service_name="svc")
_TIME_RANGE = TimeRange(start=0, end=60, step=10)
_METRICS = {
    name: metrics_v1.Metric(
        name=name,
        title=Title("Metric"),
        unit=metrics_v1.Unit(metrics_v1.DecimalNotation("")),
        color=metrics_v1.Color.BLUE,
    )
    for name in ("cpu_user", "cpu_system", "cpu_cores", "util", "temp")
}


def _id(text: str) -> str:
    return text


def _column(name: str) -> RRDMetric:
    return RRDMetric(host_name="h", service_name="svc", metric_name=MetricName(name))


def _ts(*values: float | None, time_range: TimeRange = _TIME_RANGE) -> TimeSeries:
    return TimeSeries(time_range=time_range, values=list(values))


class _FakeRRD:
    """An RRDSource serving both performance data and time series for the whole lifecycle."""

    def __init__(
        self,
        *,
        performance_data: Mapping[ServiceRef, PerformanceData],
        time_series: Mapping[RRDMetric, TimeSeries],
    ) -> None:
        self._performance_data = performance_data
        self._time_series = time_series
        # The runtime parameters of every fetch_time_series call, so a test can assert how the two
        # entry points drove the source.
        self.time_series_requests: list[tuple[TimeRange, ConsolidationFunction]] = []

    def fetch_performance_data(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, PerformanceData]:
        return {
            service: self._performance_data[service]
            for service in services
            if service in self._performance_data
        }

    def fetch_time_series(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[RRDMetric, TimeSeries]:
        self.time_series_requests.append((time_range, consolidation_function))
        return {
            metric: self._time_series[metric]
            for metric in rrd_metrics
            if metric in self._time_series
        }


def _discover(
    rrd: _FakeRRD,
    registered_graphs: Sequence[graphs_v1.Graph],
    *,
    translations: Sequence[translations_v1.Translation] = (),
) -> Sequence[DiscoveredGraph]:
    # Compose the discovery steps the way the GUI does: fetch -> build -> evaluate -> wrap.
    translated_metrics = fetch_translated_metrics(
        services=[_SERVICE],
        translations=translations,
        metrics=_METRICS,
        localizer=_id,
        rrd=rrd,
    )
    graphs = build_graphs(
        service=_SERVICE,
        registered_graphs=registered_graphs,
        metrics=_METRICS,
        localizer=_id,
        available=translated_metrics.get(_SERVICE, {}),
    )
    return [
        DiscoveredGraph(
            graph=graph,
            title=evaluated.title,
            vertical_range=evaluated.vertical_range,
            stacks=evaluated.stacks,
            lines=evaluated.lines,
        )
        for graph, evaluated in zip(
            graphs,
            evaluate_graphs(
                graphs=graphs,
                translated_metrics=translated_metrics,
                consolidation_function=ConsolidationFunction.AVERAGE,
                time_range=_TIME_RANGE,
                rrd=rrd,
            ),
        )
    ]


def _refresh(
    rrd: _FakeRRD,
    discovered: Sequence[DiscoveredGraph],
    *,
    translations: Sequence[translations_v1.Translation] = (),
) -> Sequence[EvaluatedGraph]:
    return update_graph_data(
        graphs=[discovered.graph for discovered in discovered],
        translations=translations,
        metrics=_METRICS,
        localizer=_id,
        consolidation_function=ConsolidationFunction.AVERAGE,
        time_range=_TIME_RANGE,
        rrd=rrd,
    )


def _assert_refresh_reproduces_discovery(
    discovered: Sequence[DiscoveredGraph],
    evaluated: Sequence[EvaluatedGraph],
) -> None:
    assert [graph.name for graph in evaluated] == [graph.graph.name for graph in discovered]
    for discovered_graph, evaluated_graph in zip(discovered, evaluated):
        assert evaluated_graph.title == discovered_graph.title
        assert evaluated_graph.vertical_range == discovered_graph.vertical_range
        assert evaluated_graph.stacks == discovered_graph.stacks
        assert evaluated_graph.lines == discovered_graph.lines


def test_update_reproduces_a_title_expression_for_a_non_drawn_metric() -> None:
    # The title references cpu_cores, a metric the graph does not plot (only cpu_user is drawn).
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title('CPU - _EXPRESSION:{"metric": "cpu_cores", "scalar": "max"} cores'),
        simple_lines=["cpu_user"],
    )
    rrd = _FakeRRD(
        performance_data={
            _SERVICE: PerformanceData(
                check_command="check_mk-cpu",
                values=[
                    PerformanceValue(metric_name=MetricName("cpu_user"), value=3.0),
                    PerformanceValue(metric_name=MetricName("cpu_cores"), value=8.0, maximum=8.0),
                ],
            )
        },
        time_series={_column("cpu_user"): _ts(1.0, 2.0, 3.0, 4.0, 5.0, 6.0)},
    )

    [discovered] = _discover(rrd, [plugin])
    assert discovered.title == "CPU - 8 cores"

    evaluated = _refresh(rrd, [discovered])
    _assert_refresh_reproduces_discovery([discovered], evaluated)


def test_update_reproduces_a_compound_and_simple_line_graph() -> None:
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU utilization"),
        compound_lines=["cpu_user", "cpu_system"],
        simple_lines=["util"],
        minimal_range=graphs_v1.MinimalRange(0, 100),
    )
    rrd = _FakeRRD(
        performance_data={
            _SERVICE: PerformanceData(
                check_command="check_mk-cpu",
                values=[
                    PerformanceValue(metric_name=MetricName("cpu_user"), value=10.0),
                    PerformanceValue(metric_name=MetricName("cpu_system"), value=20.0),
                    PerformanceValue(metric_name=MetricName("util"), value=30.0),
                ],
            )
        },
        time_series={
            _column("cpu_user"): _ts(1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
            _column("cpu_system"): _ts(2.0, 2.0, 2.0, 2.0, 2.0, 2.0),
            _column("util"): _ts(3.0, 3.0, 3.0, 3.0, 3.0, 3.0),
        },
    )

    [discovered] = _discover(rrd, [plugin])
    # A compound group becomes a stack; the simple line stays a line.
    assert [curve.value for stack in discovered.stacks for curve in stack.members] == [10.0, 20.0]
    assert [line.curve.value for line in discovered.lines] == [30.0]

    evaluated = _refresh(rrd, [discovered])
    _assert_refresh_reproduces_discovery([discovered], evaluated)


def test_update_reproduces_a_fallback_single_metric_graph() -> None:
    # No registered plugin: every metric becomes its own single-metric fallback graph.
    rrd = _FakeRRD(
        performance_data={
            _SERVICE: PerformanceData(
                check_command="check_mk-cpu",
                values=[PerformanceValue(metric_name=MetricName("temp"), value=42.0)],
            )
        },
        time_series={_column("temp"): _ts(40.0, 41.0, 42.0, 43.0, 44.0, 45.0)},
    )

    [discovered] = _discover(rrd, [])
    assert discovered.graph.name == "temp"
    assert [curve.value for stack in discovered.stacks for curve in stack.members] == [42.0]

    evaluated = _refresh(rrd, [discovered])
    _assert_refresh_reproduces_discovery([discovered], evaluated)


def test_update_reproduces_a_renamed_and_scaled_metric() -> None:
    # The raw column "temperature" is renamed to "temp" and scaled by 2; both value and series are
    # scaled, and the rename means the raw column is the one fetched.
    translations = [
        translations_v1.Translation(
            name="t",
            check_commands=[translations_v1.PassiveCheck("cpu")],
            translations={"temperature": translations_v1.RenameToAndScaleBy("temp", 2.0)},
        )
    ]
    rrd = _FakeRRD(
        performance_data={
            _SERVICE: PerformanceData(
                check_command="check_mk-cpu",
                values=[PerformanceValue(metric_name=MetricName("temperature"), value=21.0)],
            )
        },
        time_series={_column("temperature"): _ts(10.0, 10.0, 10.0, 10.0, 10.0, 10.0)},
    )

    [discovered] = _discover(rrd, [], translations=translations)
    assert discovered.graph.name == "temp"
    [curve] = [curve for stack in discovered.stacks for curve in stack.members]
    assert curve.value == 42.0
    assert curve.time_series == _ts(20.0, 20.0, 20.0, 20.0, 20.0, 20.0)

    evaluated = _refresh(rrd, [discovered], translations=translations)
    _assert_refresh_reproduces_discovery([discovered], evaluated)


def test_update_reproduces_several_graphs_in_order() -> None:
    # A matching plugin plus an unclaimed metric yields two graphs; refreshing keeps both in order.
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])
    rrd = _FakeRRD(
        performance_data={
            _SERVICE: PerformanceData(
                check_command="check_mk-cpu",
                values=[
                    PerformanceValue(metric_name=MetricName("cpu_user"), value=5.0),
                    PerformanceValue(metric_name=MetricName("temp"), value=42.0),
                ],
            )
        },
        time_series={
            _column("cpu_user"): _ts(5.0, 5.0, 5.0, 5.0, 5.0, 5.0),
            _column("temp"): _ts(42.0, 42.0, 42.0, 42.0, 42.0, 42.0),
        },
    )

    discovered = _discover(rrd, [plugin])
    assert [graph.graph.name for graph in discovered] == ["cpu", "temp"]

    evaluated = _refresh(rrd, discovered)
    _assert_refresh_reproduces_discovery(discovered, evaluated)


def test_update_reproduces_a_natively_gridded_series() -> None:
    # The source serves a finer native grid (step 5); both entry points align it to the requested
    # grid (step 10) the same way.
    native = TimeRange(start=0, end=60, step=5)
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])
    rrd = _FakeRRD(
        performance_data={
            _SERVICE: PerformanceData(
                check_command="check_mk-cpu",
                values=[PerformanceValue(metric_name=MetricName("cpu_user"), value=1.0)],
            )
        },
        time_series={
            _column("cpu_user"): _ts(
                1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, time_range=native
            )
        },
    )

    [discovered] = _discover(rrd, [plugin])
    # The fetched series is aligned to the six requested points.
    assert len(discovered.lines[0].curve.time_series.values) == 6
    assert discovered.lines[0].curve.time_series.time_range == _TIME_RANGE

    evaluated = _refresh(rrd, [discovered])
    _assert_refresh_reproduces_discovery([discovered], evaluated)


# --- the realistic case: data has moved on by the time the graph is refreshed -------------------


def _cpu_rrd(*, value: float, series: TimeSeries) -> _FakeRRD:
    plugin_metric = PerformanceValue(metric_name=MetricName("cpu_user"), value=value)
    return _FakeRRD(
        performance_data={
            _SERVICE: PerformanceData(check_command="check_mk-cpu", values=[plugin_metric])
        },
        time_series={_column("cpu_user"): series},
    )


def test_refresh_picks_up_a_changed_value_and_series() -> None:
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])
    at_discovery = _cpu_rrd(value=3.0, series=_ts(1.0, 1.0, 1.0, 1.0, 1.0, 1.0))
    later = _cpu_rrd(value=9.0, series=_ts(7.0, 8.0, 9.0, 10.0, 11.0, 12.0))

    [discovered] = _discover(at_discovery, [plugin])
    assert discovered.lines[0].curve.value == 3.0

    [evaluated] = _refresh(later, [discovered])

    # Same graph identity, but the curve now carries the newer value and series.
    assert evaluated.name == discovered.graph.name
    assert evaluated.lines[0].curve.value == 9.0
    assert evaluated.lines[0].curve.time_series == _ts(7.0, 8.0, 9.0, 10.0, 11.0, 12.0)


def test_refresh_picks_up_a_changed_title_scalar() -> None:
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title('CPU - _EXPRESSION:{"metric": "cpu_cores", "scalar": "max"} cores'),
        simple_lines=["cpu_user"],
    )

    def _rrd(cores_max: float) -> _FakeRRD:
        return _FakeRRD(
            performance_data={
                _SERVICE: PerformanceData(
                    check_command="check_mk-cpu",
                    values=[
                        PerformanceValue(metric_name=MetricName("cpu_user"), value=3.0),
                        PerformanceValue(
                            metric_name=MetricName("cpu_cores"), value=cores_max, maximum=cores_max
                        ),
                    ],
                )
            },
            time_series={_column("cpu_user"): _ts(1.0, 1.0, 1.0, 1.0, 1.0, 1.0)},
        )

    [discovered] = _discover(_rrd(8.0), [plugin])
    assert discovered.title == "CPU - 8 cores"

    # The machine grew to 16 cores; the refreshed title reflects the new scalar.
    [evaluated] = _refresh(_rrd(16.0), [discovered])
    assert evaluated.title == "CPU - 16 cores"


def test_refresh_drops_a_curve_whose_metric_disappeared() -> None:
    plugin = graphs_v1.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
    )
    at_discovery = _FakeRRD(
        performance_data={
            _SERVICE: PerformanceData(
                check_command="check_mk-cpu",
                values=[
                    PerformanceValue(metric_name=MetricName("cpu_user"), value=3.0),
                    PerformanceValue(metric_name=MetricName("cpu_system"), value=4.0),
                ],
            )
        },
        time_series={
            _column("cpu_user"): _ts(3.0, 3.0, 3.0, 3.0, 3.0, 3.0),
            _column("cpu_system"): _ts(4.0, 4.0, 4.0, 4.0, 4.0, 4.0),
        },
    )
    # On refresh cpu_system no longer reports any data.
    later = _FakeRRD(
        performance_data={
            _SERVICE: PerformanceData(
                check_command="check_mk-cpu",
                values=[PerformanceValue(metric_name=MetricName("cpu_user"), value=3.0)],
            )
        },
        time_series={_column("cpu_user"): _ts(3.0, 3.0, 3.0, 3.0, 3.0, 3.0)},
    )

    [discovered] = _discover(at_discovery, [plugin])
    assert [line.curve.title for line in discovered.lines] == ["Metric", "Metric"]

    [evaluated] = _refresh(later, [discovered])
    # The curve of the vanished metric is dropped; cpu_user's line remains.
    assert len(evaluated.lines) == 1
    assert evaluated.lines[0].curve.time_series == _ts(3.0, 3.0, 3.0, 3.0, 3.0, 3.0)
