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
    build_service_graphs,
    ConsolidationFunction,
    EvaluatedGraph,
    fetch_performance_data,
    Graph,
    Line,
    match_graph_for_services,
    MetricName,
    PerformanceData,
    PerformanceValue,
    Quantity,
    RRDMetric,
    Rule,
    ScalarOf,
    ScalarType,
    ServiceRef,
    Stack,
    TimeRange,
    TimeSeries,
    update_graphs,
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


def _service() -> ServiceRef:
    return ServiceRef(host_name="h", service_name="svc")


def _rrd(name: MetricName) -> RRDMetric:
    return RRDMetric(
        host_name="h",
        service_name="svc",
        metric_name=name,
    )


def _dstack(*quantities: Quantity) -> Stack:
    return Stack(members=[build_curve(q, _METRICS, _id) for q in quantities], inverse=False)


def _dline(quantity: Quantity) -> Line:
    return Line(curve=build_curve(quantity, _METRICS, _id), inverse=False)


_FALLBACK_RULE_TYPES = (
    ScalarType.WARNING,
    ScalarType.CRITICAL,
    ScalarType.LOWER_WARNING,
    ScalarType.LOWER_CRITICAL,
)


def _fallback(name: MetricName) -> Graph:
    # The fallback single-metric graph the engine builds for an unclaimed metric: the metric as a
    # stacked curve plus the four warn / crit (and lower) threshold rules as ScalarOf quantities, each
    # with its display resolved.
    return Graph(
        name=name,
        title=name,
        graph_type=_KIND,
        stacks=[_dstack(_rrd(name))],
        rules=[
            Rule(
                curve=build_curve(
                    ScalarOf(metric=_rrd(name), scalar_type=scalar_type), _METRICS, _id
                ),
                inverse=False,
            )
            for scalar_type in _FALLBACK_RULE_TYPES
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

    def fetch_performance_data(
        self,
        services: Sequence[ServiceRef],  # noqa: ARG002
    ) -> Mapping[ServiceRef, PerformanceData]:
        return self._performance_response

    def fetch_time_series(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        consolidation_function: ConsolidationFunction,  # noqa: ARG002
        time_range: TimeRange,  # noqa: ARG002
    ) -> Mapping[RRDMetric, TimeSeries]:
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
) -> Sequence[Graph]:
    # Discovery fetches the performance data only to match / build the structure; it stores none.
    performance_data = fetch_performance_data(services=[service], translations=[], rrd=rrd)
    return build_service_graphs(
        service=service,
        registered_graphs=registered_graphs,
        metrics=_METRICS,
        localizer=_id,
        graph_type=_KIND,
        available=performance_data.get(service, {}),
    )


def _evaluate(discovered: Graph, rrd: _FakeFetchRRD) -> EvaluatedGraph:
    # Resolve the structure's display, then run the sole update entry point over a fresh fetch.
    [evaluated] = update_graphs(
        graphs=[discovered],
        translations=[],
        consolidation_function=ConsolidationFunction.AVERAGE,
        time_range=_time_range(),
        rrd=rrd,
    )
    return evaluated


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

    assert discovered == _fallback(cpu_user)
    # The single metric is drawn as a stacked curve carrying its value.
    assert [
        curve.value for stack in _evaluate(discovered, rrd).stacks for curve in stack.members
    ] == [1.0]
    assert _evaluate(discovered, rrd).lines == []


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
    assert discovered[0] == parse_graph_from_api(plugin, service, _METRICS, _id, graph_type=_KIND)
    # A plain title without expressions is carried through unchanged.
    assert _evaluate(discovered[0], rrd).title == "CPU"
    assert [line.curve.value for line in _evaluate(discovered[0], rrd).lines] == [1.0, 1.0]


def test_discover_template_graphs_emits_default_graph_for_unclaimed_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    extra = MetricName("extra")
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])
    registered_graphs = [plugin]
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user), _perf(extra))})

    [matched, fallback] = _discover(service, registered_graphs, rrd=rrd)

    assert matched == parse_graph_from_api(plugin, service, _METRICS, _id, graph_type=_KIND)
    assert fallback == _fallback(extra)


def test_discover_template_graphs_rejects_plugin_when_required_metric_missing() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
    )
    registered_graphs = [plugin]
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user))})

    [fallback] = _discover(service, registered_graphs, rrd=rrd)

    assert fallback == _fallback(cpu_user)


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

    assert discovered == parse_graph_from_api(plugin, service, _METRICS, _id, graph_type=_KIND)


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

    assert all(d.name != "cpu" for d in discovered)


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

    assert discovered == parse_graph_from_api(plugin, service, _METRICS, _id, graph_type=_KIND)


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

    assert discovered == parse_graph_from_api(plugin, service, _METRICS, _id, graph_type=_KIND)


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
    assert {d.name for d in discovered} == {"cpu", "cpu_system"}
    cpu = next(d for d in discovered if d.name == "cpu")
    assert [line.curve.value for line in _evaluate(cpu, rrd).lines] == [1.0]
    assert [rule.value for rule in _evaluate(cpu, rrd).rules] == [50.0]


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
    assert {d.name for d in discovered} == {"cpu", "cpu_system"}
    cpu = next(d for d in discovered if d.name == "cpu")
    assert [line.curve.value for line in _evaluate(cpu, rrd).lines] == [1.0]
    assert [rule.value for rule in _evaluate(cpu, rrd).rules] == [50.0]


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
    assert _evaluate(discovered, rrd).title == "CPU - 8 cores"
    assert "_EXPRESSION:" in discovered.title


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

    assert _evaluate(discovered, rrd).title == "CPU"


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

    assert [d.name for d in discovered] == ["cpu"]
    assert _evaluate(discovered[0], rrd).title == "CPU"


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
    assert {d.name for d in discovered} == {"cpu", "cpu_user"}
    cpu = next(d for d in discovered if d.name == "cpu")
    assert _evaluate(cpu, rrd).title == "CPU - 8 cores"


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
    assert _dline(_rrd(predict)) in discovered[0].lines
    # cpu_user and its predictive companion are both drawn (neither dropped for missing data).
    assert len(_evaluate(discovered[0], rrd).lines) == 2


def test_discover_template_graphs_adds_predictive_lines_to_a_fallback_graph() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    predict = MetricName("predict_cpu_user")
    registered_graphs: list[graphs_v1.Graph] = []
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user), _perf(predict))})

    discovered = _discover(service, registered_graphs, rrd=rrd)

    # Only the cpu_user fallback graph is emitted; its predictive companion is added as a line.
    assert [d.name for d in discovered] == ["cpu_user"]
    assert _dline(_rrd(predict)) in discovered[0].lines


def test_discover_template_graphs_ignores_a_predictive_metric_without_its_base() -> None:
    service = _service()
    predict = MetricName("predict_cpu_user")
    registered_graphs: list[graphs_v1.Graph] = []
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(predict))})

    assert _discover(service, registered_graphs, rrd=rrd) == []


def test_match_graph_for_services_adds_predictive_lines_per_service() -> None:
    # The combined primitive matches one plugin across several services; like the template path it
    # adds a predictive line wherever predict_* exists for that service, and only there.
    cpu_user = MetricName("cpu_user")
    predict = MetricName("predict_cpu_user")
    with_predict = ServiceRef(host_name="h1", service_name="svc")
    without_predict = ServiceRef(host_name="h2", service_name="svc")
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])

    graphs = match_graph_for_services(
        services=[with_predict, without_predict],
        graph=plugin,
        metrics=_METRICS,
        localizer=_id,
        graph_type=_KIND,
        available={with_predict: {cpu_user, predict}, without_predict: {cpu_user}},
    )

    assert len(graphs) == 2
    assert (
        Line(
            curve=build_curve(
                RRDMetric(host_name="h1", service_name="svc", metric_name=predict), _METRICS, _id
            ),
            inverse=False,
        )
        in graphs[0].lines
    )
    assert all(
        not (
            isinstance(line.curve.quantity, RRDMetric)
            and line.curve.quantity.metric_name == predict
        )
        for line in graphs[1].lines
    )


def test_build_service_graphs_builds_threshold_rules_for_fallback_graphs() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    rrd = _FakeFetchRRD(performance_response={service: _perf_data(_perf(cpu_user, warning=80.0))})
    available = fetch_performance_data(services=[service], translations=[], rrd=rrd).get(
        service, {}
    )

    graphs = build_service_graphs(
        service=service,
        registered_graphs=[],
        metrics=_METRICS,
        localizer=_id,
        graph_type=_KIND,
        available=available,
    )
    # The fallback single-metric graph carries the four warn / crit (and lower) threshold rules as
    # ScalarOf quantities, their labels / colours resolved from the scalar type.
    [graph] = [g for g in graphs if g.name == cpu_user]
    assert [rule.curve.quantity for rule in graph.rules] == [
        ScalarOf(metric=_rrd(cpu_user), scalar_type=scalar_type)
        for scalar_type in _FALLBACK_RULE_TYPES
    ]
