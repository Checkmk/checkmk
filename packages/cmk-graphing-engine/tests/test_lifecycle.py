#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""End-to-end tests of the discover -> update lifecycle, exercising the entry points
together.

Discovery (build_service_graphs) builds the display-resolved Graph; update_graph
fetches the performance data and time series afresh
and evaluates each into an EvaluatedGraph. Discovery stores no data, so a refresh always re-fetches.
Each test fakes a different shape of performance / time series data to cover the pipeline from
several angles.
"""

from collections.abc import Mapping, Sequence

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import (
    build_service_graphs,
    ConsolidationFunction,
    EvaluatedGraph,
    fetch_performance_data,
    Graph,
    MetricName,
    PerformanceData,
    PerformanceValue,
    RRDMetric,
    ServiceRef,
    TimeRange,
    TimeSeries,
    update_graph,
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
        # The runtime parameters of every fetch_time_series call, so a test can assert how update
        # drove the source.
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
) -> Sequence[Graph]:
    # Discovery the way the GUI does it: fetch performance data only, then build the structural
    # graphs from the metric names that are present.
    performance_data = fetch_performance_data(
        services=[_SERVICE],
        translations=translations,
        rrd=rrd,
    )
    return build_service_graphs(
        service=_SERVICE,
        registered_graphs=registered_graphs,
        metrics=_METRICS,
        localizer=_id,
        available=performance_data.get(_SERVICE, {}),
        graph_type="test",
    )


def _refresh(
    rrd: _FakeRRD,
    discovered: Sequence[Graph],
    *,
    translations: Sequence[translations_v1.Translation] = (),
) -> Sequence[EvaluatedGraph]:
    # Evaluate every discovered graph through the sole update entry point (display already resolved).
    return update_graph(
        graphs=list(discovered),
        translations=translations,
        consolidation_function=ConsolidationFunction.AVERAGE,
        time_range=_TIME_RANGE,
        rrd=rrd,
    )


def _evaluate(
    discovered: Graph,
    rrd: _FakeRRD,
    *,
    translations: Sequence[translations_v1.Translation] = (),
) -> EvaluatedGraph:
    [evaluated] = _refresh(rrd, [discovered], translations=translations)
    return evaluated


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

    # cpu_cores is referenced only by the title, so it is not claimed and gets its own fallback
    # graph alongside the cpu plugin graph.
    discovered = _discover(rrd, [plugin])
    cpu = next(d for d in discovered if d.name == "cpu")
    assert _evaluate(cpu, rrd).title == "CPU - 8 cores"


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
    evaluated = _evaluate(discovered, rrd)
    # A compound group becomes a stack; the simple line stays a line.
    assert [curve.value for stack in evaluated.stacks for curve in stack.members] == [10.0, 20.0]
    assert [line.curve.value for line in evaluated.lines] == [30.0]


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
    assert discovered.name == "temp"
    evaluated = _evaluate(discovered, rrd)
    assert [curve.value for stack in evaluated.stacks for curve in stack.members] == [42.0]


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
    assert discovered.name == "temp"
    evaluated = _evaluate(discovered, rrd, translations=translations)
    [curve] = [curve for stack in evaluated.stacks for curve in stack.members]
    assert curve.value == 42.0
    assert curve.time_series == _ts(20.0, 20.0, 20.0, 20.0, 20.0, 20.0)


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
    assert [graph.name for graph in discovered] == ["cpu", "temp"]

    evaluated = _refresh(rrd, discovered)
    assert [graph.name for graph in evaluated] == ["cpu", "temp"]


def test_update_reproduces_a_natively_gridded_series() -> None:
    # The source serves a finer native grid (step 5); update aligns it to the requested grid (step
    # 10).
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
    evaluated = _evaluate(discovered, rrd)
    # The fetched series is aligned to the six requested points.
    assert len(evaluated.lines[0].curve.time_series.values) == 6
    assert evaluated.lines[0].curve.time_series.time_range == _TIME_RANGE


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
    assert _evaluate(discovered, at_discovery).lines[0].curve.value == 3.0

    [evaluated] = _refresh(later, [discovered])

    # Same graph identity, but the curve now carries the newer value and series (update re-fetches).
    assert evaluated.name == discovered.name
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

    # cpu_cores is referenced only by the title, so it is not claimed and gets its own fallback
    # graph; pick the cpu plugin graph out of the discovered set.
    discovered = _discover(_rrd(8.0), [plugin])
    cpu = next(d for d in discovered if d.name == "cpu")
    assert _evaluate(cpu, _rrd(8.0)).title == "CPU - 8 cores"

    # The machine grew to 16 cores; the refreshed title reflects the new scalar.
    evaluated = _refresh(_rrd(16.0), discovered)
    cpu_evaluated = next(e for e in evaluated if e.name == "cpu")
    assert cpu_evaluated.title == "CPU - 16 cores"


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
    assert [line.curve.attributes.title for line in _evaluate(discovered, at_discovery).lines] == [
        "Metric",
        "Metric",
    ]

    [evaluated] = _refresh(later, [discovered])
    # The curve of the vanished metric is dropped; cpu_user's line remains.
    assert len(evaluated.lines) == 1
    assert evaluated.lines[0].curve.time_series == _ts(3.0, 3.0, 3.0, 3.0, 3.0, 3.0)
