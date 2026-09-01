#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.graphing.v1 import graphs as graphs_v1
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title
from cmk.graphing.v2_unstable import graphs as graphs_v2_unstable
from cmk.graphing.v2_unstable import metrics as metrics_v2_unstable
from cmk.graphing_engine import (
    build_curve,
    build_matched_graphs,
    ConsolidationFunction,
    Constant,
    Difference,
    evaluate_graphs,
    EvaluatedGraph,
    FetchedData,
    Graph,
    HostName,
    Line,
    MetricName,
    MetricProtocol,
    MinimalRange,
    PerformanceData,
    QuantityProtocol,
    RRDMetric,
    Rule,
    ScalarKind,
    ScalarOf,
    Service,
    ServiceName,
    Stack,
    Sum,
    TimeRange,
    TimeSeries,
)
from cmk.graphing_engine._from_api import parse_graph_from_api


def _id(s: str) -> str:
    return s


_KIND = "test"


# Uniform definitions for every metric referenced below: the title "Metric", plain decimal unit,
# blue. _rrd() below mirrors what the parser produces from these.
_TITLE = Title("Metric")
_METRICS = {
    name: metrics_v1.Metric(
        name=name,
        title=_TITLE,
        unit=metrics_v1.Unit(metrics_v1.DecimalNotation("")),
        color=metrics_v1.Color.BLUE,
    )
    for name in ("cpu_user", "cpu_system", "cpu_iowait", "util", "extra", "if_in", "if_out")
}


def _time_range() -> TimeRange:
    return TimeRange(start=0, end=60, step=10)


def _service() -> Service:
    return Service(host_name=HostName("h"), service_name=ServiceName("svc"))


def _rrd(name: MetricName) -> RRDMetric:
    return RRDMetric(
        host_name=HostName("h"),
        service_name=ServiceName("svc"),
        metric_name=name,
    )


def _dstack(*quantities: QuantityProtocol) -> Stack:
    return Stack(members=[build_curve(q, _id, _METRICS) for q in quantities], inverse=False)


def _dline(quantity: QuantityProtocol) -> Line:
    return Line(curve=build_curve(quantity, _id, _METRICS), inverse=False)


_FALLBACK_RULE_TYPES = (
    ScalarKind.WARNING,
    ScalarKind.CRITICAL,
    ScalarKind.LOWER_WARNING,
    ScalarKind.LOWER_CRITICAL,
)


def _fallback(name: MetricName) -> Graph:
    # The fallback single-metric graph the engine builds for an unclaimed metric: the metric as a
    # stacked curve plus the four warn / crit (and lower) threshold rules as ScalarOf quantities, each
    # with its display resolved.
    return Graph(
        name=name,
        title=_TITLE.localize(_id),
        kind=_KIND,
        stacks=[_dstack(_rrd(name))],
        rules=[
            Rule(
                curve=build_curve(
                    ScalarOf(metric=_rrd(name), scalar_kind=scalar_kind), _id, _METRICS
                ),
                inverse=False,
            )
            for scalar_kind in _FALLBACK_RULE_TYPES
        ],
    )


def _perf(
    name: MetricName,
    *,
    lower_warning: float | None = None,
    lower_critical: float | None = None,
    warning: float | None = None,
    critical: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> tuple[MetricName, PerformanceData]:
    return name, PerformanceData(
        value=1.0,
        lower_warning=lower_warning,
        lower_critical=lower_critical,
        warning=warning,
        critical=critical,
        minimum=minimum,
        maximum=maximum,
    )


def _perf_data(
    *values: tuple[MetricName, PerformanceData],
) -> Mapping[MetricName, PerformanceData]:
    return dict(values)


class _FakeRRDFetchMetricNames:
    def __init__(
        self, performance_response: Mapping[Service, Mapping[MetricName, PerformanceData]]
    ) -> None:
        self._performance_response = performance_response

    def __call__(self) -> Mapping[Service, frozenset[MetricName]]:
        return {service: frozenset(raw) for service, raw in self._performance_response.items()}


class _FakeRRDFetchData:
    def __init__(
        self,
        performance_response: Mapping[Service, Mapping[MetricName, PerformanceData]] | None = None,
        time_series_response: Mapping[RRDMetric, TimeSeries] | None = None,
    ) -> None:
        self.performance_response = performance_response or {}
        self._time_series_response = time_series_response or {}

    def __call__(
        self,
        metrics: Sequence[MetricProtocol],
        *,
        consolidation_function: ConsolidationFunction,  # noqa: ARG002
        time_range: TimeRange,  # noqa: ARG002
    ) -> Mapping[MetricProtocol, Sequence[FetchedData]]:
        result: dict[MetricProtocol, Sequence[FetchedData]] = {}
        for metric in metrics:
            if not isinstance(metric, RRDMetric):
                continue
            service = Service(host_name=metric.host_name, service_name=metric.service_name)
            raw = self.performance_response.get(service)
            performance_data = None if raw is None else raw.get(metric.metric_name)
            series = self._time_series_response.get(metric)
            if performance_data is None and series is None:
                continue
            result[metric] = [FetchedData(performance_data=performance_data, time_series=series)]
        return result


def _discover(
    registered_graphs: Sequence[
        graphs_v1.Graph
        | graphs_v1.Bidirectional
        | graphs_v2_unstable.Graph
        | graphs_v2_unstable.Bidirectional
    ],
    *,
    fetch_data: _FakeRRDFetchData,
    graph_name: str | None = None,
) -> Sequence[Graph]:
    return build_matched_graphs(
        localizer=_id,
        fetch_metric_names=_FakeRRDFetchMetricNames(fetch_data.performance_response),
        kind=_KIND,
        registered_graphs=registered_graphs,
        registered_metrics=_METRICS,
        graph_name=graph_name,
    )


def _evaluate(discovered: Graph, fetch_data: _FakeRRDFetchData) -> EvaluatedGraph:
    # Resolve the structure's display, then run the sole update entry point over a fresh fetch.
    [evaluated] = evaluate_graphs(
        consolidation_function=ConsolidationFunction.AVERAGE,
        time_range=_time_range(),
        graphs=[discovered],
        fetch_data=fetch_data,
    )
    return evaluated


def test_build_matched_graphs_empty_service_returns_no_graphs() -> None:
    service = _service()
    registered_graphs = [graphs_v1.Graph(name="g", title=Title("t"), simple_lines=["x"])]
    fetch_data = _FakeRRDFetchData(performance_response={service: _perf_data()})

    assert _discover(registered_graphs, fetch_data=fetch_data) == []


def test_build_matched_graphs_falls_back_to_single_metric_graph_for_unclaimed_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    registered_graphs: list[graphs_v1.Graph] = []
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user, warning=80.0, critical=90.0))}
    )

    [discovered] = _discover(registered_graphs, fetch_data=fetch_data)

    assert discovered == _fallback(cpu_user)
    # The single metric is drawn as a stacked curve carrying its value.
    assert [
        curve.value for stack in _evaluate(discovered, fetch_data).stacks for curve in stack.members
    ] == [1.0]
    assert _evaluate(discovered, fetch_data).lines == []


def test_build_matched_graphs_titles_a_fallback_graph_after_its_metric() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    fetch_data = _FakeRRDFetchData(performance_response={service: _perf_data(_perf(cpu_user))})

    [discovered] = _discover([], fetch_data=fetch_data)

    assert discovered.name == cpu_user
    assert discovered.title == "Metric"


def test_build_matched_graphs_matching_plugin_claims_its_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v1.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
    )
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user, warning=80.0), _perf(cpu_system))}
    )

    discovered = _discover(registered_graphs, fetch_data=fetch_data)

    assert len(discovered) == 1
    assert discovered[0] == parse_graph_from_api(plugin, [service], _id, _METRICS, kind=_KIND)
    # A plain title without expressions is carried through unchanged.
    assert _evaluate(discovered[0], fetch_data).title == "CPU"
    assert [line.curve.value for line in _evaluate(discovered[0], fetch_data).lines] == [1.0, 1.0]


def test_build_matched_graphs_emits_default_graph_for_unclaimed_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    extra = MetricName("extra")
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user), _perf(extra))}
    )

    [matched, fallback] = _discover(registered_graphs, fetch_data=fetch_data)

    assert matched == parse_graph_from_api(plugin, [service], _id, _METRICS, kind=_KIND)
    assert fallback == _fallback(extra)


def test_build_matched_graphs_emits_fallback_graphs_in_metric_name_order() -> None:
    service = _service()
    unclaimed = [
        MetricName("util"),
        MetricName("if_in"),
        MetricName("extra"),
        MetricName("cpu_user"),
        MetricName("if_out"),
    ]
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(*(_perf(name) for name in unclaimed))}
    )

    graphs = _discover([], fetch_data=fetch_data)

    assert [graph.name for graph in graphs] == sorted(unclaimed)


def test_build_matched_graphs_filters_to_the_requested_graph_name() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    extra = MetricName("extra")
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user), _perf(extra))}
    )

    def _matched(graph_name: str) -> Sequence[Graph]:
        return build_matched_graphs(
            localizer=_id,
            fetch_metric_names=_FakeRRDFetchMetricNames(fetch_data.performance_response),
            kind=_KIND,
            registered_graphs=[plugin],
            registered_metrics=_METRICS,
            graph_name=graph_name,
        )

    assert [graph.name for graph in _matched("cpu")] == ["cpu"]
    # The legacy "METRIC_<name>" id addresses the engine's single-metric fallback graph "<name>".
    assert [graph.name for graph in _matched("extra")] == ["extra"]
    assert [graph.name for graph in _matched("METRIC_extra")] == ["extra"]
    assert list(_matched("does_not_exist")) == []


def test_build_matched_graphs_answers_a_single_metric_request_a_plugin_claims() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])
    fetch_data = _FakeRRDFetchData(performance_response={service: _perf_data(_perf(cpu_user))})

    # The plug-in claims the metric, so discovery offers its graph alone.
    assert [graph.name for graph in _discover([plugin], fetch_data=fetch_data)] == ["cpu"]

    [requested] = _discover([plugin], fetch_data=fetch_data, graph_name=f"METRIC_{cpu_user}")

    assert requested == _fallback(cpu_user)


def test_build_matched_graphs_answers_no_single_metric_request_for_an_absent_metric() -> None:
    service = _service()
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(MetricName("cpu_user")))}
    )

    assert list(_discover([], fetch_data=fetch_data, graph_name="METRIC_absent")) == []


def test_build_matched_graphs_rejects_plugin_when_required_metric_missing() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
    )
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(performance_response={service: _perf_data(_perf(cpu_user))})

    [fallback] = _discover(registered_graphs, fetch_data=fetch_data)

    assert fallback == _fallback(cpu_user)


def test_build_matched_graphs_optional_missing_metric_still_matches() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=["cpu_user", "cpu_iowait"],
        optional=["cpu_iowait"],
    )
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(performance_response={service: _perf_data(_perf(cpu_user))})

    [discovered] = _discover(registered_graphs, fetch_data=fetch_data)

    assert discovered == parse_graph_from_api(plugin, [service], _id, _METRICS, kind=_KIND)


def test_build_matched_graphs_conflicting_metric_present_rejects_plugin() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    util = MetricName("util")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=["cpu_user"],
        conflicting=["util"],
    )
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user), _perf(util))}
    )

    discovered = _discover(registered_graphs, fetch_data=fetch_data)

    assert all(d.name != "cpu" for d in discovered)


def test_build_matched_graphs_matches_v2_unstable_graph() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v2_unstable.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
    )
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user), _perf(cpu_system))}
    )

    [discovered] = _discover(registered_graphs, fetch_data=fetch_data)

    assert discovered == parse_graph_from_api(plugin, [service], _id, _METRICS, kind=_KIND)


def test_build_matched_graphs_matches_v2_unstable_bidirectional() -> None:
    service = _service()
    in_ = MetricName("if_in")
    out = MetricName("if_out")
    plugin = graphs_v2_unstable.Bidirectional(
        name="if",
        title=Title("Interface"),
        lower=graphs_v2_unstable.Graph(name="in", title=Title("In"), simple_lines=["if_in"]),
        upper=graphs_v2_unstable.Graph(name="out", title=Title("Out"), simple_lines=["if_out"]),
    )
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(in_), _perf(out))}
    )

    [discovered] = _discover(registered_graphs, fetch_data=fetch_data)

    assert discovered == parse_graph_from_api(plugin, [service], _id, _METRICS, kind=_KIND)


def test_build_matched_graphs_carries_scalars_for_v2_unstable_scalar_quantity() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v2_unstable.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=["cpu_user", metrics_v2_unstable.LowerWarningOf("cpu_system")],
    )
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(
        performance_response={
            service: _perf_data(_perf(cpu_user), _perf(cpu_system, lower_warning=50.0))
        }
    )

    discovered = _discover(registered_graphs, fetch_data=fetch_data)

    # cpu_user is drawn with its value; the scalar reference becomes a rule at cpu_system's lower
    # warning. cpu_system is only referenced as a threshold, so it is not claimed and also gets its
    # own fallback graph.
    assert {d.name for d in discovered} == {"cpu", "cpu_system"}
    cpu = next(d for d in discovered if d.name == "cpu")
    assert [line.curve.value for line in _evaluate(cpu, fetch_data).lines] == [1.0]
    assert [rule.value for rule in _evaluate(cpu, fetch_data).rules] == [50.0]


def test_build_matched_graphs_carries_scalars_for_scalar_referenced_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=["cpu_user", metrics_v1.WarningOf("cpu_system")],
    )
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user), _perf(cpu_system, warning=50.0))}
    )

    discovered = _discover(registered_graphs, fetch_data=fetch_data)

    # cpu_user is drawn with its value; the scalar reference becomes a rule at cpu_system's warning.
    # cpu_system is only referenced as a threshold, so it is not claimed and also gets its own
    # fallback graph.
    assert {d.name for d in discovered} == {"cpu", "cpu_system"}
    cpu = next(d for d in discovered if d.name == "cpu")
    assert [line.curve.value for line in _evaluate(cpu, fetch_data).lines] == [1.0]
    assert [rule.value for rule in _evaluate(cpu, fetch_data).rules] == [50.0]


def test_build_matched_graphs_evaluates_the_title_expression() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title('CPU - _EXPRESSION:{"metric": "cpu_user", "scalar": "max"} cores'),
        simple_lines=["cpu_user"],
    )
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user, maximum=8.0))}
    )

    [discovered] = _discover(registered_graphs, fetch_data=fetch_data)

    # The evaluated title is exposed via title; the graph keeps its raw title.
    assert _evaluate(discovered, fetch_data).title == "CPU - 8 cores"
    assert "_EXPRESSION:" in discovered.title


def test_build_matched_graphs_title_expression_falls_back_when_unresolvable() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title('CPU - _EXPRESSION:{"metric": "cpu_user", "scalar": "max"} cores'),
        simple_lines=["cpu_user"],
    )
    registered_graphs = [plugin]
    # cpu_user is available (so the plugin matches) but carries no maximum scalar.
    fetch_data = _FakeRRDFetchData(performance_response={service: _perf_data(_perf(cpu_user))})

    [discovered] = _discover(registered_graphs, fetch_data=fetch_data)

    assert _evaluate(discovered, fetch_data).title == "CPU"


def test_build_matched_graphs_matches_despite_a_metric_referenced_only_in_the_title() -> None:
    service = _service()
    util = MetricName("util")
    # cpu_user is referenced by the title only (not drawn as a line).
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title('CPU - _EXPRESSION:{"metric": "cpu_user", "scalar": "max"} cores'),
        simple_lines=["util"],
    )
    registered_graphs = [plugin]
    # cpu_user (referenced only by the title) is missing, but the title is not part of matching, so
    # the plugin still matches on its drawn metric util; the title expression falls back.
    fetch_data = _FakeRRDFetchData(performance_response={service: _perf_data(_perf(util))})

    discovered = _discover(registered_graphs, fetch_data=fetch_data)

    assert [d.name for d in discovered] == ["cpu"]
    assert _evaluate(discovered[0], fetch_data).title == "CPU"


def test_build_matched_graphs_does_not_claim_a_metric_referenced_only_in_the_title() -> None:
    service = _service()
    util = MetricName("util")
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title('CPU - _EXPRESSION:{"metric": "cpu_user", "scalar": "max"} cores'),
        simple_lines=["util"],
    )
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(util), _perf(cpu_user, maximum=8.0))}
    )

    discovered = _discover(registered_graphs, fetch_data=fetch_data)

    # The plugin matches and its title resolves against cpu_user, but cpu_user is only referenced by
    # the title, so it is not claimed and still gets its own fallback graph.
    assert {d.name for d in discovered} == {"cpu", "cpu_user"}
    cpu = next(d for d in discovered if d.name == "cpu")
    assert _evaluate(cpu, fetch_data).title == "CPU - 8 cores"


def test_build_matched_graphs_title_metric_does_not_make_a_match() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    # The drawn metric util is missing; the title references cpu_user, which is present.
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title('CPU - _EXPRESSION:{"metric": "cpu_user"} cores'),
        simple_lines=["util"],
    )
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(performance_response={service: _perf_data(_perf(cpu_user))})

    discovered = _discover(registered_graphs, fetch_data=fetch_data)

    # A metric referenced only by the title cannot make a match: the plugin is rejected for its
    # missing drawn metric, and cpu_user only gets its own fallback graph.
    assert [d.name for d in discovered] == [str(cpu_user)]


def test_build_matched_graphs_adds_predictive_lines_to_a_matched_graph() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    predict = MetricName("predict_cpu_user")
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])
    registered_graphs = [plugin]
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user), _perf(predict))}
    )

    discovered = _discover(registered_graphs, fetch_data=fetch_data)

    # The predictive metric is drawn alongside cpu_user, not as a graph of its own.
    assert len(discovered) == 1
    assert _dline(_rrd(predict)) in discovered[0].lines
    # cpu_user and its predictive companion are both drawn (neither dropped for missing data).
    assert len(_evaluate(discovered[0], fetch_data).lines) == 2


def test_build_matched_graphs_adds_predictive_lines_to_a_fallback_graph() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    predict = MetricName("predict_cpu_user")
    registered_graphs: list[graphs_v1.Graph] = []
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user), _perf(predict))}
    )

    discovered = _discover(registered_graphs, fetch_data=fetch_data)

    # Only the cpu_user fallback graph is emitted; its predictive companion is added as a line.
    assert [d.name for d in discovered] == ["cpu_user"]
    assert _dline(_rrd(predict)) in discovered[0].lines


def test_build_matched_graphs_ignores_a_predictive_metric_without_its_base() -> None:
    service = _service()
    predict = MetricName("predict_cpu_user")
    registered_graphs: list[graphs_v1.Graph] = []
    fetch_data = _FakeRRDFetchData(performance_response={service: _perf_data(_perf(predict))})

    assert _discover(registered_graphs, fetch_data=fetch_data) == []


def test_build_matched_graphs_builds_threshold_rules_for_fallback_graphs() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user, warning=80.0))}
    )
    graphs = build_matched_graphs(
        localizer=_id,
        fetch_metric_names=_FakeRRDFetchMetricNames(fetch_data.performance_response),
        kind=_KIND,
        registered_graphs=[],
        registered_metrics=_METRICS,
    )
    # The fallback single-metric graph carries the four warn / crit (and lower) threshold rules as
    # ScalarOf quantities, their labels / colours resolved from the scalar type.
    [graph] = [g for g in graphs if g.name == cpu_user]
    assert [rule.curve.quantity for rule in graph.rules] == [
        ScalarOf(metric=_rrd(cpu_user), scalar_kind=scalar_kind)
        for scalar_kind in _FALLBACK_RULE_TYPES
    ]


def test_build_matched_graphs_keeps_threshold_rules_when_adding_predictive_lines() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    predict = MetricName("predict_cpu_user")
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user, warning=80.0), _perf(predict))}
    )
    graphs = build_matched_graphs(
        localizer=_id,
        fetch_metric_names=_FakeRRDFetchMetricNames(fetch_data.performance_response),
        kind=_KIND,
        registered_graphs=[],
        registered_metrics=_METRICS,
    )
    # Injecting the predictive companion line must not drop the fallback threshold rules.
    [graph] = [g for g in graphs if g.name == cpu_user]
    assert _dline(_rrd(predict)) in graph.lines
    assert [rule.curve.quantity for rule in graph.rules] == [
        ScalarOf(metric=_rrd(cpu_user), scalar_kind=scalar_kind)
        for scalar_kind in _FALLBACK_RULE_TYPES
    ]


# --- multiple services -----------------------------------------------------------------------------


def _services() -> tuple[Service, Service]:
    return (
        Service(host_name=HostName("h1"), service_name=ServiceName("svc")),
        Service(host_name=HostName("h2"), service_name=ServiceName("svc")),
    )


def _rrd_on(service: Service, name: MetricName) -> RRDMetric:
    return RRDMetric(
        host_name=service.host_name, service_name=service.service_name, metric_name=name
    )


class _SumQuantityBuilder:
    # Stand-in for a real aggregating QuantityBuilderProtocol (e.g. the pro CombinedAggregation):
    # wraps what one drawn quantity is per service in the engine's own Sum.
    def __call__(self, per_object: Sequence[QuantityProtocol]) -> QuantityProtocol:
        return Sum(summands=list(per_object))


def _discover_combined(
    registered_graphs: Sequence[
        graphs_v1.Graph
        | graphs_v1.Bidirectional
        | graphs_v2_unstable.Graph
        | graphs_v2_unstable.Bidirectional
    ],
    *,
    fetch_data: _FakeRRDFetchData,
) -> Sequence[Graph]:
    return build_matched_graphs(
        localizer=_id,
        fetch_metric_names=_FakeRRDFetchMetricNames(fetch_data.performance_response),
        kind=_KIND,
        registered_graphs=registered_graphs,
        registered_metrics=_METRICS,
        quantity_builder=_SumQuantityBuilder(),
    )


def test_build_matched_graphs_aggregates_a_drawn_metric_across_services() -> None:
    h1, h2 = _services()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])
    fetch_data = _FakeRRDFetchData(
        performance_response={h1: _perf_data(_perf(cpu_user)), h2: _perf_data(_perf(cpu_user))}
    )

    [discovered] = _discover_combined([plugin], fetch_data=fetch_data)

    # The drawn metric is wrapped in the builder's aggregation over both services' RRDMetrics.
    [line] = discovered.lines
    assert line.curve.quantity == Sum(summands=[_rrd_on(h1, cpu_user), _rrd_on(h2, cpu_user)])
    # Both services contribute; the evaluated value is their sum.
    assert [line.curve.value for line in _evaluate(discovered, fetch_data).lines] == [2.0]


def test_build_matched_graphs_builds_a_drawn_operation_per_service() -> None:
    h1, h2 = _services()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=[
            metrics_v1.Difference(
                Title("Difference"),
                metrics_v1.Color.GREEN,
                minuend="cpu_user",
                subtrahend="cpu_system",
            )
        ],
    )
    fetch_data = _FakeRRDFetchData(
        performance_response={
            h1: _perf_data(_perf(cpu_user), _perf(cpu_system)),
            h2: _perf_data(_perf(cpu_user), _perf(cpu_system)),
        }
    )

    [discovered] = _discover_combined([plugin], fetch_data=fetch_data)

    # The builder combines one difference per service, rather than the difference taking two
    # cross-service quantities as its operands - which no operation can have.
    [line] = discovered.lines
    quantity = line.curve.quantity
    assert isinstance(quantity, Sum)
    operands = []
    for summand in quantity.summands:
        assert isinstance(summand, Difference)
        operands.append((summand.minuend, summand.subtrahend))
    assert operands == [
        (_rrd_on(h1, cpu_user), _rrd_on(h1, cpu_system)),
        (_rrd_on(h2, cpu_user), _rrd_on(h2, cpu_system)),
    ]
    assert [line.curve.value for line in _evaluate(discovered, fetch_data).lines] == [0.0]


def test_build_matched_graphs_resolves_a_nested_scalar_per_service() -> None:
    h1, h2 = _services()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=[
            metrics_v1.Difference(
                Title("Headroom"),
                metrics_v1.Color.GREEN,
                minuend=metrics_v1.MaximumOf("cpu_user", metrics_v1.Color.GREEN),
                subtrahend="cpu_user",
            )
        ],
    )
    fetch_data = _FakeRRDFetchData(
        performance_response={
            h1: _perf_data(_perf(cpu_user)),
            h2: _perf_data(_perf(cpu_user)),
        }
    )

    [discovered] = _discover_combined([plugin], fetch_data=fetch_data)

    # A threshold names the metric of the service its expression was built for, not of the first
    # matched one.
    [line] = discovered.lines
    quantity = line.curve.quantity
    assert isinstance(quantity, Sum)
    thresholds = []
    for summand in quantity.summands:
        assert isinstance(summand, Difference)
        assert isinstance(summand.minuend, ScalarOf)
        assert summand.minuend.scalar_kind is ScalarKind.MAXIMUM
        thresholds.append(summand.minuend.metric)
    assert thresholds == [_rrd_on(h1, cpu_user), _rrd_on(h2, cpu_user)]


def test_build_matched_graphs_drops_rules_and_predictive_for_multiple_services() -> None:
    h1, h2 = _services()
    cpu_user = MetricName("cpu_user")
    predict = MetricName("predict_cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=["cpu_user", metrics_v1.WarningOf("cpu_user")],
    )
    fetch_data = _FakeRRDFetchData(
        performance_response={
            h1: _perf_data(_perf(cpu_user, warning=80.0), _perf(predict)),
            h2: _perf_data(_perf(cpu_user, warning=80.0)),
        }
    )

    discovered = _discover_combined([plugin], fetch_data=fetch_data)

    # The scalar threshold would be a rule for a single service; across services it is dropped, and
    # the predictive metric is neither drawn nor given a graph of its own.
    assert [d.name for d in discovered] == ["cpu"]
    assert discovered[0].rules == ()


def test_build_matched_graphs_falls_back_across_services() -> None:
    h1, h2 = _services()
    extra = MetricName("extra")
    fetch_data = _FakeRRDFetchData(
        performance_response={h1: _perf_data(_perf(extra)), h2: _perf_data(_perf(extra))}
    )

    [discovered] = _discover_combined([], fetch_data=fetch_data)

    assert discovered.name == extra
    [member] = discovered.stacks[0].members
    assert member.quantity == Sum(summands=[_rrd_on(h1, extra), _rrd_on(h2, extra)])
    assert discovered.rules == ()


def test_build_matched_graphs_needs_all_required_metrics_on_one_service() -> None:
    h1, h2 = _services()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v1.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
    )
    fetch_data = _FakeRRDFetchData(
        performance_response={h1: _perf_data(_perf(cpu_user)), h2: _perf_data(_perf(cpu_system))}
    )

    discovered = _discover_combined([plugin], fetch_data=fetch_data)

    # No single service has both required metrics, so the plugin is not matched (per-service, like
    # legacy combined discovery); each metric falls back to its own aggregated single-metric graph.
    assert {d.name for d in discovered} == {"cpu_user", "cpu_system"}


def test_build_matched_graphs_matches_via_a_service_without_the_conflicting_metric() -> None:
    h1, h2 = _services()
    cpu_user = MetricName("cpu_user")
    util = MetricName("util")
    plugin = graphs_v1.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user"], conflicting=["util"]
    )
    fetch_data = _FakeRRDFetchData(
        performance_response={
            h1: _perf_data(_perf(cpu_user)),
            h2: _perf_data(_perf(cpu_user), _perf(util)),
        }
    )

    discovered = _discover_combined([plugin], fetch_data=fetch_data)

    # h2 carries the conflicting metric, but h1 does not, so the plugin still matches via h1.
    assert "cpu" in {d.name for d in discovered}


def _graph_with_a_quantity_bound() -> graphs_v1.Graph:
    return graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        minimal_range=graphs_v1.MinimalRange(
            0, metrics_v1.MaximumOf("cpu_user", metrics_v1.Color.GREEN)
        ),
        simple_lines=["cpu_user"],
    )


def test_build_matched_graphs_keeps_a_quantity_range_bound_for_one_service() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    fetch_data = _FakeRRDFetchData(
        performance_response={service: _perf_data(_perf(cpu_user, maximum=100.0))}
    )

    [discovered] = _discover([_graph_with_a_quantity_bound()], fetch_data=fetch_data)

    assert discovered.vertical_range is not None
    assert discovered.vertical_range.lower == 0
    upper = discovered.vertical_range.upper
    assert isinstance(upper, ScalarOf)
    assert upper.metric == _rrd(cpu_user)
    assert upper.scalar_kind is ScalarKind.MAXIMUM


def test_build_matched_graphs_drops_a_quantity_range_bound_for_multiple_services() -> None:
    h1, h2 = _services()
    cpu_user = MetricName("cpu_user")
    fetch_data = _FakeRRDFetchData(
        performance_response={
            h1: _perf_data(_perf(cpu_user, maximum=100.0)),
            h2: _perf_data(_perf(cpu_user, maximum=200.0)),
        }
    )

    [discovered] = _discover_combined([_graph_with_a_quantity_bound()], fetch_data=fetch_data)

    # The numeric end is kept; the threshold end belongs to no one matched object, so it is dropped
    # rather than resolved against an arbitrary one.
    assert discovered.vertical_range == MinimalRange(lower=0, upper=None)


def test_build_matched_graphs_drops_a_wholly_quantity_range_for_multiple_services() -> None:
    h1, h2 = _services()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        minimal_range=graphs_v1.MinimalRange(
            metrics_v1.MinimumOf("cpu_user", metrics_v1.Color.GREEN),
            metrics_v1.MaximumOf("cpu_user", metrics_v1.Color.GREEN),
        ),
        simple_lines=["cpu_user"],
    )
    fetch_data = _FakeRRDFetchData(
        performance_response={
            h1: _perf_data(_perf(cpu_user, minimum=0.0, maximum=100.0)),
            h2: _perf_data(_perf(cpu_user, minimum=0.0, maximum=200.0)),
        }
    )

    [discovered] = _discover_combined([plugin], fetch_data=fetch_data)

    # Neither end survives, so there is no range rather than one holding nothing.
    assert discovered.vertical_range is None


def test_build_matched_graphs_keeps_a_constant_range_bound_for_multiple_services() -> None:
    h1, h2 = _services()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        minimal_range=graphs_v1.MinimalRange(
            0,
            metrics_v1.Constant(
                Title("Ceiling"),
                metrics_v1.Unit(metrics_v1.DecimalNotation("")),
                metrics_v1.Color.GRAY,
                100.0,
            ),
        ),
        simple_lines=["cpu_user"],
    )
    fetch_data = _FakeRRDFetchData(
        performance_response={h1: _perf_data(_perf(cpu_user)), h2: _perf_data(_perf(cpu_user))}
    )

    [discovered] = _discover_combined([plugin], fetch_data=fetch_data)

    # A bound of constants alone names no metric, so it needs no object and survives.
    assert discovered.vertical_range is not None
    assert discovered.vertical_range.lower == 0
    upper = discovered.vertical_range.upper
    assert isinstance(upper, Constant)
    assert upper.value == 100.0


def test_build_matched_graphs_lets_a_kept_end_win_over_a_dropped_one_when_bidirectional() -> None:
    h1, h2 = _services()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v1.Bidirectional(
        name="cpu",
        title=Title("CPU"),
        upper=graphs_v1.Graph(
            name="upper",
            title=Title("Upper"),
            minimal_range=graphs_v1.MinimalRange(
                0, metrics_v1.MaximumOf("cpu_user", metrics_v1.Color.GRAY)
            ),
            simple_lines=["cpu_user"],
        ),
        lower=graphs_v1.Graph(
            name="lower",
            title=Title("Lower"),
            minimal_range=graphs_v1.MinimalRange(0, 50),
            simple_lines=["cpu_system"],
        ),
    )
    fetch_data = _FakeRRDFetchData(
        performance_response={
            h1: _perf_data(_perf(cpu_user, maximum=100.0), _perf(cpu_system)),
            h2: _perf_data(_perf(cpu_user, maximum=200.0), _perf(cpu_system)),
        }
    )

    [discovered] = _discover_combined([plugin], fetch_data=fetch_data)

    # The upper half's threshold end is dropped, so the lower half's numeric end is the range - where
    # a threshold resolved against one arbitrary object would have masked it.
    assert discovered.vertical_range == MinimalRange(lower=0, upper=50)
