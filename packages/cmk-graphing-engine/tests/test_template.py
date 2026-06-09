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
    AutoPrecision,
    CommonOptions,
    ConsolidationFunction,
    DecimalNotation,
    discover_template_graphs,
    Graph,
    Metric,
    MetricName,
    parse_graph_from_api,
    RRDMetric,
    RRDSource,
    Scalars,
    ServiceRef,
    StackGroup,
    TemperatureUnit,
    TemplateDiscoveryOptions,
    TemplateOptions,
    TimeRange,
    TimeSeries,
    TranslatedMetric,
    Unit,
)


def _id(s: str) -> str:
    return s


# Uniform definitions for every metric referenced below: the title "Metric", plain decimal unit,
# blue. _metric() below mirrors what the parser produces from these.
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


def _common() -> CommonOptions:
    return CommonOptions(
        time_range=TimeRange(start=0, end=60, step=10),
        temperature_unit=TemperatureUnit.CELSIUS,
    )


def _service() -> ServiceRef:
    return ServiceRef(site_id="s", host_name="h", service_name="svc")


def _rrd(name: MetricName) -> RRDMetric:
    return RRDMetric(
        host_name="h",
        service_name="svc",
        metric_name=name,
        consolidation_function=ConsolidationFunction.AVERAGE,
    )


def _metric(name: MetricName) -> Metric:
    return Metric(
        rrd_metric=_rrd(name),
        title="Metric",
        unit=Unit(notation=DecimalNotation(""), precision=AutoPrecision(2)),
        color="#28a2f3",
    )


def _translated(name: MetricName, *, bounds: Scalars = Scalars()) -> TranslatedMetric:
    return TranslatedMetric(
        name=name,
        value=1.0,
        bounds=bounds,
        originals=[RRDSource(service=_service(), metric_name=name, scale=1.0)],
    )


class _FakeFetchRRD:
    def __init__(
        self,
        translated_metrics_response: Mapping[ServiceRef, Mapping[MetricName, TranslatedMetric]]
        | None = None,
    ) -> None:
        self._translated_metrics_response = translated_metrics_response or {}
        self.translated_metrics_calls: list[tuple[ServiceRef, ...]] = []

    def translated_metrics(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, Mapping[MetricName, TranslatedMetric]]:
        self.translated_metrics_calls.append(tuple(services))
        return self._translated_metrics_response

    def time_series(
        self,
        keys: Sequence[RRDSource],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDSource, TimeSeries]:
        raise NotImplementedError


def test_discover_template_graphs_empty_service_returns_no_graphs() -> None:
    service = _service()
    options = TemplateDiscoveryOptions(
        common=_common(),
        service=service,
        consolidation_function=ConsolidationFunction.AVERAGE,
        metrics=_METRICS,
        localizer=_id,
        registered_graphs=[graphs_v1.Graph(name="g", title=Title("t"), simple_lines=["x"])],
    )
    rrd = _FakeFetchRRD(translated_metrics_response={service: {}})

    assert discover_template_graphs(options, rrd=rrd) == []


def test_discover_template_graphs_falls_back_to_single_metric_graph_for_unclaimed_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_user_bounds = Scalars(warning=80.0, critical=90.0)
    options = TemplateDiscoveryOptions(
        common=_common(),
        service=service,
        consolidation_function=ConsolidationFunction.AVERAGE,
        metrics=_METRICS,
        localizer=_id,
        registered_graphs=[],
    )
    rrd = _FakeFetchRRD(
        translated_metrics_response={
            service: {cpu_user: _translated(cpu_user, bounds=cpu_user_bounds)}
        }
    )

    [discovered] = discover_template_graphs(options, rrd=rrd)

    assert discovered.graph == Graph(
        name=cpu_user, title=cpu_user, stack_groups=[StackGroup(members=[_metric(cpu_user)])]
    )
    assert discovered.options == TemplateOptions(common=_common(), service=service)
    assert discovered.scalars == {_rrd(cpu_user): cpu_user_bounds}


def test_discover_template_graphs_matching_plugin_claims_its_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v1.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
    )
    options = TemplateDiscoveryOptions(
        common=_common(),
        service=service,
        consolidation_function=ConsolidationFunction.AVERAGE,
        metrics=_METRICS,
        localizer=_id,
        registered_graphs=[plugin],
    )
    cpu_user_bounds = Scalars(warning=80.0)
    rrd = _FakeFetchRRD(
        translated_metrics_response={
            service: {
                cpu_user: _translated(cpu_user, bounds=cpu_user_bounds),
                cpu_system: _translated(cpu_system),
            }
        }
    )

    discovered = discover_template_graphs(options, rrd=rrd)

    assert len(discovered) == 1
    assert discovered[0].graph == parse_graph_from_api(
        plugin, _id, service, ConsolidationFunction.AVERAGE, _METRICS
    )
    assert discovered[0].scalars == {_rrd(cpu_user): cpu_user_bounds}


def test_discover_template_graphs_emits_default_graph_for_unclaimed_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    extra = MetricName("extra")
    plugin = graphs_v1.Graph(name="cpu", title=Title("CPU"), simple_lines=["cpu_user"])
    options = TemplateDiscoveryOptions(
        common=_common(),
        service=service,
        consolidation_function=ConsolidationFunction.AVERAGE,
        metrics=_METRICS,
        localizer=_id,
        registered_graphs=[plugin],
    )
    rrd = _FakeFetchRRD(
        translated_metrics_response={
            service: {cpu_user: _translated(cpu_user), extra: _translated(extra)}
        }
    )

    [matched, fallback] = discover_template_graphs(options, rrd=rrd)

    assert matched.graph == parse_graph_from_api(
        plugin, _id, service, ConsolidationFunction.AVERAGE, _METRICS
    )
    assert fallback.graph == Graph(
        name=extra, title=extra, stack_groups=[StackGroup(members=[_metric(extra)])]
    )


def test_discover_template_graphs_rejects_plugin_when_required_metric_missing() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
    )
    options = TemplateDiscoveryOptions(
        common=_common(),
        service=service,
        consolidation_function=ConsolidationFunction.AVERAGE,
        metrics=_METRICS,
        localizer=_id,
        registered_graphs=[plugin],
    )
    rrd = _FakeFetchRRD(translated_metrics_response={service: {cpu_user: _translated(cpu_user)}})

    [fallback] = discover_template_graphs(options, rrd=rrd)

    assert fallback.graph == Graph(
        name=cpu_user, title=cpu_user, stack_groups=[StackGroup(members=[_metric(cpu_user)])]
    )


def test_discover_template_graphs_optional_missing_metric_still_matches() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=["cpu_user", "cpu_iowait"],
        optional=["cpu_iowait"],
    )
    options = TemplateDiscoveryOptions(
        common=_common(),
        service=service,
        consolidation_function=ConsolidationFunction.AVERAGE,
        metrics=_METRICS,
        localizer=_id,
        registered_graphs=[plugin],
    )
    rrd = _FakeFetchRRD(translated_metrics_response={service: {cpu_user: _translated(cpu_user)}})

    [discovered] = discover_template_graphs(options, rrd=rrd)

    assert discovered.graph == parse_graph_from_api(
        plugin, _id, service, ConsolidationFunction.AVERAGE, _METRICS
    )


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
    options = TemplateDiscoveryOptions(
        common=_common(),
        service=service,
        consolidation_function=ConsolidationFunction.AVERAGE,
        metrics=_METRICS,
        localizer=_id,
        registered_graphs=[plugin],
    )
    rrd = _FakeFetchRRD(
        translated_metrics_response={
            service: {cpu_user: _translated(cpu_user), util: _translated(util)}
        }
    )

    discovered = discover_template_graphs(options, rrd=rrd)

    assert all(d.graph.name != "cpu" for d in discovered)


def test_discover_template_graphs_matches_v2_unstable_graph() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v2_unstable.Graph(
        name="cpu", title=Title("CPU"), simple_lines=["cpu_user", "cpu_system"]
    )
    options = TemplateDiscoveryOptions(
        common=_common(),
        service=service,
        consolidation_function=ConsolidationFunction.AVERAGE,
        metrics=_METRICS,
        localizer=_id,
        registered_graphs=[plugin],
    )
    rrd = _FakeFetchRRD(
        translated_metrics_response={
            service: {
                cpu_user: _translated(cpu_user),
                cpu_system: _translated(cpu_system),
            }
        }
    )

    [discovered] = discover_template_graphs(options, rrd=rrd)

    assert discovered.graph == parse_graph_from_api(
        plugin, _id, service, ConsolidationFunction.AVERAGE, _METRICS
    )


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
    options = TemplateDiscoveryOptions(
        common=_common(),
        service=service,
        consolidation_function=ConsolidationFunction.AVERAGE,
        metrics=_METRICS,
        localizer=_id,
        registered_graphs=[plugin],
    )
    rrd = _FakeFetchRRD(
        translated_metrics_response={service: {in_: _translated(in_), out: _translated(out)}}
    )

    [discovered] = discover_template_graphs(options, rrd=rrd)

    assert discovered.graph == parse_graph_from_api(
        plugin, _id, service, ConsolidationFunction.AVERAGE, _METRICS
    )


def test_discover_template_graphs_carries_scalars_for_v2_unstable_scalar_quantity() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v2_unstable.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=["cpu_user", metrics_v2_unstable.LowerWarningOf("cpu_system")],
    )
    options = TemplateDiscoveryOptions(
        common=_common(),
        service=service,
        consolidation_function=ConsolidationFunction.AVERAGE,
        metrics=_METRICS,
        localizer=_id,
        registered_graphs=[plugin],
    )
    cpu_system_bounds = Scalars(warning=50.0)
    rrd = _FakeFetchRRD(
        translated_metrics_response={
            service: {
                cpu_user: _translated(cpu_user),
                cpu_system: _translated(cpu_system, bounds=cpu_system_bounds),
            }
        }
    )

    [discovered] = discover_template_graphs(options, rrd=rrd)

    assert discovered.scalars == {_rrd(cpu_system): cpu_system_bounds}


def test_discover_template_graphs_carries_scalars_for_scalar_referenced_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = graphs_v1.Graph(
        name="cpu",
        title=Title("CPU"),
        simple_lines=["cpu_user", metrics_v1.WarningOf("cpu_system")],
    )
    options = TemplateDiscoveryOptions(
        common=_common(),
        service=service,
        consolidation_function=ConsolidationFunction.AVERAGE,
        metrics=_METRICS,
        localizer=_id,
        registered_graphs=[plugin],
    )
    cpu_system_bounds = Scalars(warning=50.0)
    rrd = _FakeFetchRRD(
        translated_metrics_response={
            service: {
                cpu_user: _translated(cpu_user),
                cpu_system: _translated(cpu_system, bounds=cpu_system_bounds),
            }
        }
    )

    [discovered] = discover_template_graphs(options, rrd=rrd)

    assert discovered.scalars == {_rrd(cpu_system): cpu_system_bounds}
