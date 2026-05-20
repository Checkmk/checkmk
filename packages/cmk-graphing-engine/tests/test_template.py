#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.graphing_engine import (
    CommonOptions,
    ConsolidationFunction,
    discover_template_graphs,
    Graph,
    MetricName,
    RRDKey,
    Scalars,
    ServiceRef,
    TemperatureUnit,
    TemplateDiscoveryOptions,
    TemplateOptions,
    TimeRange,
    TimeSeries,
    TranslatedMetric,
    WarningOf,
)


def _common() -> CommonOptions:
    return CommonOptions(
        time_range=TimeRange(start=0, end=60, step=10),
        consolidation_function=ConsolidationFunction.AVERAGE,
        temperature_unit=TemperatureUnit.CELSIUS,
    )


def _service() -> ServiceRef:
    return ServiceRef(site_id="s", host_name="h", service_name="svc")


def _translated(name: MetricName, *, bounds: Scalars = Scalars()) -> TranslatedMetric:
    return TranslatedMetric(
        name=name,
        value=1.0,
        bounds=bounds,
        originals=[RRDKey(service=_service(), metric_name=name, scale=1.0)],
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
        keys: Sequence[RRDKey],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDKey, TimeSeries]:
        raise NotImplementedError


def test_discover_template_graphs_empty_service_returns_no_graphs() -> None:
    service = _service()
    options = TemplateDiscoveryOptions(
        common=_common(),
        service=service,
        registered_graphs=[Graph(name="g", title="t", simple_lines=[MetricName("x")])],
    )
    rrd = _FakeFetchRRD(translated_metrics_response={service: {}})

    assert discover_template_graphs(options, rrd=rrd) == []


def test_discover_template_graphs_falls_back_to_single_metric_graph_for_unclaimed_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_user_bounds = Scalars(warning=80.0, critical=90.0)
    options = TemplateDiscoveryOptions(common=_common(), service=service, registered_graphs=[])
    rrd = _FakeFetchRRD(
        translated_metrics_response={
            service: {cpu_user: _translated(cpu_user, bounds=cpu_user_bounds)}
        }
    )

    [discovered] = discover_template_graphs(options, rrd=rrd)

    assert discovered.graph == Graph(name=cpu_user, title=cpu_user, simple_lines=[cpu_user])
    assert discovered.options == TemplateOptions(common=_common(), service=service)
    assert discovered.scalars == {cpu_user: cpu_user_bounds}


def test_discover_template_graphs_matching_plugin_claims_its_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = Graph(name="cpu", title="CPU", simple_lines=[cpu_user, cpu_system])
    options = TemplateDiscoveryOptions(
        common=_common(), service=service, registered_graphs=[plugin]
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
    assert discovered[0].graph is plugin
    assert discovered[0].scalars == {cpu_user: cpu_user_bounds}


def test_discover_template_graphs_emits_default_graph_for_unclaimed_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    extra = MetricName("extra")
    plugin = Graph(name="cpu", title="CPU", simple_lines=[cpu_user])
    options = TemplateDiscoveryOptions(
        common=_common(), service=service, registered_graphs=[plugin]
    )
    rrd = _FakeFetchRRD(
        translated_metrics_response={
            service: {cpu_user: _translated(cpu_user), extra: _translated(extra)}
        }
    )

    [matched, fallback] = discover_template_graphs(options, rrd=rrd)

    assert matched.graph is plugin
    assert fallback.graph == Graph(name=extra, title=extra, simple_lines=[extra])


def test_discover_template_graphs_rejects_plugin_when_required_metric_missing() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = Graph(name="cpu", title="CPU", simple_lines=[cpu_user, cpu_system])
    options = TemplateDiscoveryOptions(
        common=_common(), service=service, registered_graphs=[plugin]
    )
    rrd = _FakeFetchRRD(translated_metrics_response={service: {cpu_user: _translated(cpu_user)}})

    [fallback] = discover_template_graphs(options, rrd=rrd)

    assert fallback.graph == Graph(name=cpu_user, title=cpu_user, simple_lines=[cpu_user])


def test_discover_template_graphs_optional_missing_metric_still_matches() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_iowait = MetricName("cpu_iowait")
    plugin = Graph(
        name="cpu",
        title="CPU",
        simple_lines=[cpu_user, cpu_iowait],
        optional=[cpu_iowait],
    )
    options = TemplateDiscoveryOptions(
        common=_common(), service=service, registered_graphs=[plugin]
    )
    rrd = _FakeFetchRRD(translated_metrics_response={service: {cpu_user: _translated(cpu_user)}})

    [discovered] = discover_template_graphs(options, rrd=rrd)

    assert discovered.graph is plugin


def test_discover_template_graphs_conflicting_metric_present_rejects_plugin() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    util = MetricName("util")
    plugin = Graph(
        name="cpu",
        title="CPU",
        simple_lines=[cpu_user],
        conflicting=[util],
    )
    options = TemplateDiscoveryOptions(
        common=_common(), service=service, registered_graphs=[plugin]
    )
    rrd = _FakeFetchRRD(
        translated_metrics_response={
            service: {cpu_user: _translated(cpu_user), util: _translated(util)}
        }
    )

    discovered = discover_template_graphs(options, rrd=rrd)

    assert all(d.graph is not plugin for d in discovered)


def test_discover_template_graphs_carries_scalars_for_scalar_referenced_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    plugin = Graph(
        name="cpu",
        title="CPU",
        simple_lines=[cpu_user, WarningOf(metric_name=cpu_system)],
    )
    options = TemplateDiscoveryOptions(
        common=_common(), service=service, registered_graphs=[plugin]
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

    assert discovered.scalars == {cpu_system: cpu_system_bounds}
