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
    build_graphs,
    ConsolidationFunction,
    discover_graphs,
    DiscoveredGraph,
    DiscoveredGraphs,
    evaluate_graphs,
    fetch_translated_metrics,
    Graph,
    Line,
    MetricName,
    PerformanceData,
    PerformanceValue,
    Quantity,
    RRDMetric,
    Rule,
    ScalarKind,
    ScalarOf,
    ServiceRef,
    Stack,
    TemplateOptions,
    TimeRange,
    TimeSeries,
)
from cmk.graphing_engine._from_api import parse_graph_from_api


def _id(s: str) -> str:
    return s


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


def _service() -> ServiceRef:
    return ServiceRef(host_name="h", service_name="svc")


def _rrd(name: MetricName) -> RRDMetric:
    return RRDMetric(
        host_name="h",
        service_name="svc",
        metric_name=name,
    )


def _line(quantity: Quantity) -> Line:
    return Line(quantity=quantity, inverse=False)


def _stack(*members: Quantity) -> Stack:
    return Stack(members=list(members), inverse=False)


def _perf(
    name: MetricName,
    *,
    lower_warning: float | None = None,
    lower_critical: float | None = None,
    warning: float | None = None,
    critical: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> PerformanceValue:
    return PerformanceValue(
        metric_name=name,
        value=1.0,
        lower_warning=lower_warning,
        lower_critical=lower_critical,
        warning=warning,
        critical=critical,
        minimum=minimum,
        maximum=maximum,
    )


def _perf_data(*values: PerformanceValue) -> PerformanceData:
    return PerformanceData(check_command="", values=list(values))


class _FakeFetchRRD:
    def __init__(
        self,
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
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[RRDMetric, TimeSeries]:
        self.time_series_calls.append((tuple(rrd_metrics), time_range, consolidation_function))
        return {
            metric: self._time_series_response[metric]
            for metric in rrd_metrics
            if metric in self._time_series_response
        }


def _discover(
    service: ServiceRef,
    registered_graphs: Sequence[
        graphs_v1.Graph
        | graphs_v1.Bidirectional
        | graphs_v2_unstable.Graph
        | graphs_v2_unstable.Bidirectional
    ],
    *,
    rrd: _FakeFetchRRD,
) -> Sequence[DiscoveredGraph]:
    # Compose the discovery steps the way the GUI does: fetch -> build -> evaluate -> wrap.
    translated_metrics = fetch_translated_metrics(
        services=[service], translations=[], metrics=_METRICS, localizer=_id, rrd=rrd
    )
    graphs = build_graphs(
        service=service,
        registered_graphs=registered_graphs,
        metrics=_METRICS,
        localizer=_id,
        available=translated_metrics.get(service, {}),
    )
    return [
        DiscoveredGraph(
            graph=graph,
            evaluated=evaluated,
        )
        for graph, evaluated in zip(
            graphs,
            evaluate_graphs(
                graphs=graphs,
                translated_metrics=translated_metrics,
                consolidation_function=ConsolidationFunction.AVERAGE,
                time_range=_time_range(),
                rrd=rrd,
            ),
        )
    ]


def test_discover_template_graphs_empty_service_returns_no_graphs() -> None:
    service = _service()
    registered_graphs = [graphs_v1.Graph(name="g", title=Title("t"), simple_lines=["x"])]
    rrd = _FakeFetchRRD(performance_response={service: _perf_data()})

    assert _discover(service, registered_graphs, rrd=rrd) == []


def test_discover_template_graphs_falls_back_to_single_metric_graph_for_unclaimed_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    registered_graphs: list[graphs_v1.Graph] = []
    rrd = _FakeFetchRRD(
        performance_response={service: _perf_data(_perf(cpu_user, warning=80.0, critical=90.0))}
    )

    [discovered] = _discover(service, registered_graphs, rrd=rrd)

    assert discovered.graph == Graph(name=cpu_user, title=cpu_user, stacks=[_stack(_rrd(cpu_user))])
    # The single metric is drawn as a stacked curve carrying its value.
    assert [curve.value for stack in discovered.evaluated.stacks for curve in stack.members] == [
        1.0
    ]
    assert discovered.evaluated.lines == []


def test_discovered_graphs_groups_options_with_graphs() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    registered_graphs: list[graphs_v1.Graph] = []
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user))})

    discovered = DiscoveredGraphs(
        options=TemplateOptions(
            time_range=_time_range(), consolidation_function=ConsolidationFunction.AVERAGE
        ),
        graphs=_discover(service, registered_graphs, rrd=rrd),
    )

    assert discovered.options == TemplateOptions(
        time_range=_time_range(), consolidation_function=ConsolidationFunction.AVERAGE
    )
    assert [graph.graph.name for graph in discovered.graphs] == [cpu_user]


def test_discover_template_graphs_matching_plugin_claims_its_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v1.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
    )
    registered_graphs = [plugin]
    rrd = _FakeFetchRRD(
        performance_response={service: _perf_data(_perf(cpu_user, warning=80.0), _perf(cpu_system))}
    )

    discovered = _discover(service, registered_graphs, rrd=rrd)

    assert len(discovered) == 1
    assert discovered[0].graph == parse_graph_from_api(plugin, service, _METRICS, _id)
    # A plain title without expressions is carried through unchanged.
    assert discovered[0].evaluated.title == "CPU"
    assert [line.curve.value for line in discovered[0].evaluated.lines] == [1.0, 1.0]


def test_discover_template_graphs_emits_default_graph_for_unclaimed_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    extra = MetricName("extra")
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])
    registered_graphs = [plugin]
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user), _perf(extra))})

    [matched, fallback] = _discover(service, registered_graphs, rrd=rrd)

    assert matched.graph == parse_graph_from_api(plugin, service, _METRICS, _id)
    assert fallback.graph == Graph(name=extra, title=extra, stacks=[_stack(_rrd(extra))])


def test_discover_template_graphs_rejects_plugin_when_required_metric_missing() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
    )
    registered_graphs = [plugin]
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user))})

    [fallback] = _discover(service, registered_graphs, rrd=rrd)

    assert fallback.graph == Graph(name=cpu_user, title=cpu_user, stacks=[_stack(_rrd(cpu_user))])


def test_discover_template_graphs_optional_missing_metric_still_matches() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=["cpu_user", "cpu_iowait"],
        optional=["cpu_iowait"],
    )
    registered_graphs = [plugin]
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user))})

    [discovered] = _discover(service, registered_graphs, rrd=rrd)

    assert discovered.graph == parse_graph_from_api(plugin, service, _METRICS, _id)


def test_discover_template_graphs_conflicting_metric_present_rejects_plugin() -> None:
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
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user), _perf(util))})

    discovered = _discover(service, registered_graphs, rrd=rrd)

    assert all(d.graph.name != "cpu" for d in discovered)


def test_discover_template_graphs_matches_v2_unstable_graph() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v2_unstable.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
    )
    registered_graphs = [plugin]
    rrd = _FakeFetchRRD(
        performance_response={service: _perf_data(_perf(cpu_user), _perf(cpu_system))}
    )

    [discovered] = _discover(service, registered_graphs, rrd=rrd)

    assert discovered.graph == parse_graph_from_api(plugin, service, _METRICS, _id)


def test_discover_template_graphs_matches_v2_unstable_bidirectional() -> None:
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
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(in_), _perf(out))})

    [discovered] = _discover(service, registered_graphs, rrd=rrd)

    assert discovered.graph == parse_graph_from_api(plugin, service, _METRICS, _id)


def test_discover_template_graphs_carries_scalars_for_v2_unstable_scalar_quantity() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v2_unstable.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=["cpu_user", metrics_v2_unstable.LowerWarningOf("cpu_system")],
    )
    registered_graphs = [plugin]
    rrd = _FakeFetchRRD(
        performance_response={
            service: _perf_data(_perf(cpu_user), _perf(cpu_system, lower_warning=50.0))
        }
    )

    discovered = _discover(service, registered_graphs, rrd=rrd)

    # cpu_user is drawn with its value; the scalar reference becomes a rule at cpu_system's lower
    # warning. cpu_system is only referenced as a threshold, so it is not claimed and also gets its
    # own fallback graph.
    assert {d.graph.name for d in discovered} == {"cpu", "cpu_system"}
    cpu = next(d for d in discovered if d.graph.name == "cpu")
    assert [line.curve.value for line in cpu.evaluated.lines] == [1.0]
    assert [rule.value for rule in cpu.evaluated.rules] == [50.0]


def test_discover_template_graphs_carries_scalars_for_scalar_referenced_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=["cpu_user", metrics_v1.WarningOf("cpu_system")],
    )
    registered_graphs = [plugin]
    rrd = _FakeFetchRRD(
        performance_response={service: _perf_data(_perf(cpu_user), _perf(cpu_system, warning=50.0))}
    )

    discovered = _discover(service, registered_graphs, rrd=rrd)

    # cpu_user is drawn with its value; the scalar reference becomes a rule at cpu_system's warning.
    # cpu_system is only referenced as a threshold, so it is not claimed and also gets its own
    # fallback graph.
    assert {d.graph.name for d in discovered} == {"cpu", "cpu_system"}
    cpu = next(d for d in discovered if d.graph.name == "cpu")
    assert [line.curve.value for line in cpu.evaluated.lines] == [1.0]
    assert [rule.value for rule in cpu.evaluated.rules] == [50.0]


def test_discover_template_graphs_evaluates_the_title_expression() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title('CPU - _EXPRESSION:{"metric": "cpu_user", "scalar": "max"} cores'),
        simple_lines=["cpu_user"],
    )
    registered_graphs = [plugin]
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user, maximum=8.0))})

    [discovered] = _discover(service, registered_graphs, rrd=rrd)

    # The evaluated title is exposed via title; the graph keeps its raw title.
    assert discovered.evaluated.title == "CPU - 8 cores"
    assert "_EXPRESSION:" in discovered.graph.title


def test_discover_template_graphs_title_expression_falls_back_when_unresolvable() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title('CPU - _EXPRESSION:{"metric": "cpu_user", "scalar": "max"} cores'),
        simple_lines=["cpu_user"],
    )
    registered_graphs = [plugin]
    # cpu_user is available (so the plugin matches) but carries no maximum scalar.
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user))})

    [discovered] = _discover(service, registered_graphs, rrd=rrd)

    assert discovered.evaluated.title == "CPU"


def test_discover_template_graphs_matches_despite_a_metric_referenced_only_in_the_title() -> None:
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
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(util))})

    discovered = _discover(service, registered_graphs, rrd=rrd)

    assert [d.graph.name for d in discovered] == ["cpu"]
    assert discovered[0].evaluated.title == "CPU"


def test_discover_template_graphs_does_not_claim_a_metric_referenced_only_in_the_title() -> None:
    service = _service()
    util = MetricName("util")
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title('CPU - _EXPRESSION:{"metric": "cpu_user", "scalar": "max"} cores'),
        simple_lines=["util"],
    )
    registered_graphs = [plugin]
    rrd = _FakeFetchRRD(
        performance_response={service: _perf_data(_perf(util), _perf(cpu_user, maximum=8.0))}
    )

    discovered = _discover(service, registered_graphs, rrd=rrd)

    # The plugin matches and its title resolves against cpu_user, but cpu_user is only referenced by
    # the title, so it is not claimed and still gets its own fallback graph.
    assert {d.graph.name for d in discovered} == {"cpu", "cpu_user"}
    cpu = next(d for d in discovered if d.graph.name == "cpu")
    assert cpu.evaluated.title == "CPU - 8 cores"


def test_discover_template_graphs_adds_predictive_lines_to_a_matched_graph() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    predict = MetricName("predict_cpu_user")
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])
    registered_graphs = [plugin]
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user), _perf(predict))})

    discovered = _discover(service, registered_graphs, rrd=rrd)

    # The predictive metric is drawn alongside cpu_user, not as a graph of its own.
    assert len(discovered) == 1
    graph = discovered[0].graph
    assert isinstance(graph, Graph)
    assert _line(_rrd(predict)) in graph.lines
    # cpu_user and its predictive companion are both drawn (neither dropped for missing data).
    assert len(discovered[0].evaluated.lines) == 2


def test_discover_template_graphs_adds_predictive_lines_to_a_fallback_graph() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    predict = MetricName("predict_cpu_user")
    registered_graphs: list[graphs_v1.Graph] = []
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user), _perf(predict))})

    discovered = _discover(service, registered_graphs, rrd=rrd)

    # Only the cpu_user fallback graph is emitted; its predictive companion is added as a line.
    assert [d.graph.name for d in discovered] == ["cpu_user"]
    graph = discovered[0].graph
    assert isinstance(graph, Graph)
    assert _line(_rrd(predict)) in graph.lines


def test_discover_template_graphs_ignores_a_predictive_metric_without_its_base() -> None:
    service = _service()
    predict = MetricName("predict_cpu_user")
    registered_graphs: list[graphs_v1.Graph] = []
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(predict))})

    assert _discover(service, registered_graphs, rrd=rrd) == []


def test_discover_graphs_adds_predictive_lines_per_service() -> None:
    # The combined primitive matches one plugin across several services; like the template path it
    # adds a predictive line wherever predict_* exists for that service, and only there.
    cpu_user = MetricName("cpu_user")
    predict = MetricName("predict_cpu_user")
    with_predict = ServiceRef(host_name="h1", service_name="svc")
    without_predict = ServiceRef(host_name="h2", service_name="svc")
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])

    graphs = discover_graphs(
        services=[with_predict, without_predict],
        graph=plugin,
        metrics=_METRICS,
        localizer=_id,
        available={with_predict: {cpu_user, predict}, without_predict: {cpu_user}},
    )

    assert len(graphs) == 2
    assert (
        Line(
            quantity=RRDMetric(host_name="h1", service_name="svc", metric_name=predict),
            inverse=False,
        )
        in graphs[0].lines
    )
    assert all(
        not (isinstance(line.quantity, RRDMetric) and line.quantity.metric_name == predict)
        for line in graphs[1].lines
    )


def test_build_graphs_applies_threshold_rules_to_fallback_graphs() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user, warning=80.0))})
    available = fetch_translated_metrics(
        services=[service], translations=[], metrics=_METRICS, localizer=_id, rrd=rrd
    ).get(service, {})

    def _rules(metric: RRDMetric) -> list[Rule]:
        return [
            Rule(
                quantity=ScalarOf(metric=metric, kind=ScalarKind.WARNING, color="#ff0000"),
                inverse=False,
                title="W",
            )
        ]

    graphs = build_graphs(
        service=service,
        registered_graphs=[],
        metrics=_METRICS,
        localizer=_id,
        available=available,
        threshold_rules=_rules,
    )
    # The fallback single-metric graph carries the GUI-supplied threshold rule.
    [graph] = [g for g in graphs if g.name == cpu_user]
    assert [rule.title for rule in graph.rules] == ["W"]
