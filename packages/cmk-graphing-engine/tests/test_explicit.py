#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.graphing_engine import (
    CommonOptions,
    ConsolidationFunction,
    discover_explicit_graphs,
    ExplicitDiscoveryOptions,
    ExplicitOptions,
    Graph,
    MetricName,
    RRDMetric,
    RRDSource,
    Scalars,
    ServiceRef,
    TemperatureUnit,
    TimeRange,
    TimeSeries,
    TranslatedMetric,
    WarningOf,
)


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


def test_discover_explicit_graphs_without_keys_returns_inline_definition_unchanged() -> None:
    inline = Graph(name="g", title="t")
    service = _service()
    options = ExplicitDiscoveryOptions(common=_common(), service=service, graph=inline)
    rrd = _FakeFetchRRD()

    rendered = discover_explicit_graphs(options, rrd=rrd)

    assert len(rendered) == 1
    assert rendered[0].graph is inline
    assert rendered[0].options == ExplicitOptions(common=_common(), service=service)
    assert rendered[0].scalars == {}


def test_discover_explicit_graphs_carries_scalars_for_referenced_metrics() -> None:
    service = _service()
    cpu_user = MetricName("cpu_user")
    cpu_system = MetricName("cpu_system")
    inline = Graph(
        name="cpu",
        title="CPU",
        # cpu_user as a curve; cpu_system referenced only by a scalar threshold.
        simple_lines=[_rrd(cpu_user), WarningOf(metric=_rrd(cpu_system))],
    )
    options = ExplicitDiscoveryOptions(common=_common(), service=service, graph=inline)
    cpu_user_bounds = Scalars(warning=80.0, critical=90.0)
    cpu_system_bounds = Scalars(warning=50.0, critical=70.0, minimum=0.0, maximum=100.0)
    cpu_user_key = RRDSource(service=service, metric_name=cpu_user, scale=1.0)
    rrd = _FakeFetchRRD(
        translated_metrics_response={
            service: {
                cpu_user: TranslatedMetric(
                    name=cpu_user,
                    value=42.0,
                    bounds=cpu_user_bounds,
                    originals=[cpu_user_key],
                ),
                cpu_system: TranslatedMetric(
                    name=cpu_system,
                    value=8.0,
                    bounds=cpu_system_bounds,
                    originals=[RRDSource(service=service, metric_name=cpu_system, scale=1.0)],
                ),
            }
        },
    )

    [rendered] = discover_explicit_graphs(options, rrd=rrd)

    assert rendered.scalars == {
        _rrd(cpu_user): cpu_user_bounds,
        _rrd(cpu_system): cpu_system_bounds,
    }
    assert rrd.translated_metrics_calls == [(service,)]


def test_discover_explicit_graphs_omits_scalars_for_metrics_not_in_translated_metrics() -> None:
    service = _service()
    inline = Graph(name="g", title="g", simple_lines=[_rrd(MetricName("missing_metric"))])
    options = ExplicitDiscoveryOptions(common=_common(), service=service, graph=inline)
    rrd = _FakeFetchRRD(translated_metrics_response={service: {}})

    [rendered] = discover_explicit_graphs(options, rrd=rrd)

    assert rendered.scalars == {}
