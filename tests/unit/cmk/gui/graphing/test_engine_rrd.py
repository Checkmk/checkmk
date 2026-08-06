#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pytest

from cmk.ccc.hostaddress import HostAddress
from cmk.ccc.site import SiteId
from cmk.graphing.v1 import translations
from cmk.graphing_engine import (
    ConsolidationFunction,
    EvaluatedCurve,
    EvaluatedGraph,
    HostName,
    MetricName,
    RRDMetric,
    Service,
    ServiceName,
    SiteID,
    TimeRange,
    TimeSeries,
)
from cmk.gui.config import Config
from cmk.gui.graphing._engine_dispatch import BuiltGraph, CommonGraphOptions
from cmk.gui.graphing._engine_rrd import (
    EngineRRDFetchData,
    EngineRRDFetchMetricNames,
    HOST_PSEUDO_SERVICE,
    parse_performance_data,
    PerformanceDataRow,
)
from cmk.gui.graphing._engine_template_graphs import (
    _EvaluateTemplateGraphs,
    build_template_graphs,
)
from cmk.gui.graphing._graph_templates import TemplateGraphSpecification
from cmk.livestatus_client.testing import MockLiveStatusConnection

_HOST_ROW = {
    "name": "h",
    "perf_data": "x=5",
    "metrics": ["x"],
    "check_command": "check-mk-host-ping",
}
_SERVICE_ROW = {
    "host_name": "h",
    "description": "svc",
    "perf_data": "x=5",
    "metrics": ["x"],
    "check_command": "check_mk-foo",
}


def test_parse_performance_data_merges_rrd_only_metrics() -> None:
    # Legacy reads the livestatus "metrics" column too, so a metric present in RRD but absent from
    # the live perf_data string still shows up (as a synthetic value=1 entry, deduplicated).
    parsed = parse_performance_data("live=5", "check_mk-foo", ["live", "rrd_only"], debug=False)
    by_name = {name: value.value for name, value in parsed.values.items()}
    assert by_name == {"live": 5.0, "rrd_only": 1.0}


def test_fetch_metric_names_of_a_host_reads_the_hosts_table(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    # Host metrics are addressed by the pseudo-service "_HOST_" and live on the hosts table, where
    # they are filtered by host name alone - the table switch livestatus_lql makes for the legacy
    # fetch. Queried against the services table, a host graph would find no metrics at all.
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table("hosts", [_HOST_ROW])
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name perf_data metrics check_command\nFilter: name = h\n"
    )

    with mock_livestatus():
        resolved = EngineRRDFetchMetricNames(
            host_name=HostName("h"), service_name=HOST_PSEUDO_SERVICE, debug=False
        )()

    assert resolved == {
        Service(
            site_id=SiteID("NO_SITE"), host_name=HostName("h"), service_name=HOST_PSEUDO_SERVICE
        ): frozenset({MetricName("x")})
    }


def test_fetch_metric_names_of_a_service_reads_the_services_table(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table("services", [_SERVICE_ROW])
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description perf_data metrics check_command\n"
        "Filter: host_name = h\nFilter: description = svc\nAnd: 2\n"
    )

    with mock_livestatus():
        resolved = EngineRRDFetchMetricNames(
            host_name=HostName("h"), service_name=ServiceName("svc"), debug=False
        )()

    assert resolved == {
        Service(
            site_id=SiteID("NO_SITE"), host_name=HostName("h"), service_name=ServiceName("svc")
        ): frozenset({MetricName("x")})
    }


@dataclass(frozen=True)
class _FakeMetricNamesOnSites:
    # In place of EngineRRDFetchMetricNames: the sites a host/service resolved on. Unscoped, the
    # same host/service monitored by two sites resolves on both.
    site_ids: Sequence[str]

    def __call__(self) -> Mapping[Service, frozenset[MetricName]]:
        return {
            Service(
                site_id=SiteID(site_id),
                host_name=HostName("h"),
                service_name=ServiceName("svc"),
            ): frozenset({MetricName("x")})
            for site_id in self.site_ids
        }


def _build_template_graphs(site_ids: Sequence[str]) -> Sequence[BuiltGraph]:
    return build_template_graphs(
        TemplateGraphSpecification(
            site=SiteId(site_ids[0]) if len(site_ids) == 1 else None,
            host_name=HostAddress("h"),
            service_description="svc",
        ),
        registered_graphs=[],
        registered_metrics={},
        fetch_metric_names=_FakeMetricNamesOnSites(site_ids),
    )


def test_template_graphs_are_built_for_the_site_the_service_resolved_on() -> None:
    # A template graph is single-service: its metrics carry the site the fetch resolved the service
    # on, and that is the site the graph is addressed by.
    built = _build_template_graphs(["site_b"])

    assert {
        metric.site_id
        for one in built
        for metric in one.graph.metrics()
        if isinstance(metric, RRDMetric)
    } == {SiteID("site_b")}
    assert [
        one.specification.site
        for one in built
        if isinstance(one.specification, TemplateGraphSpecification)
    ] == [SiteId("site_b")]


def test_template_graphs_cannot_be_built_from_a_service_resolved_on_two_sites() -> None:
    # The same host/service monitored by two sites leaves the single-service build with two metrics
    # where it needs one. Scoping the fetch to the caller's site is what keeps it to one; without it
    # this is the crash a service view hits.
    with pytest.raises(ValueError, match="too many values to unpack"):
        _build_template_graphs(["site_a", "site_b"])


def test_fetch_data_of_a_host_metric_reads_the_hosts_table(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    # Both fetch stages of a host metric - the performance data and the RRD series - go to the hosts
    # table as well.
    metric = RRDMetric(
        site_id=SiteID("NO_SITE"),
        host_name=HostName("h"),
        service_name=HOST_PSEUDO_SERVICE,
        metric_name=MetricName("x"),
    )
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "hosts", [{**_HOST_ROW, "rrddata:x:x.max:0:30:10": [0, 30, 10, 1.0, 2.0, 3.0]}]
    )
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name perf_data check_command\nFilter: name = h\n"
    )
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name rrddata:x:x.max:0:30:10\nFilter: name = h\n"
    )

    with mock_livestatus():
        [fetched] = EngineRRDFetchData(debug=False)(
            [metric],
            consolidation_function=ConsolidationFunction.MAX,
            time_range=TimeRange(start=0, end=30, step=10),
        )[metric]

    assert fetched.performance_data is not None
    assert fetched.performance_data.value == 5.0
    assert fetched.time_series is not None
    assert list(fetched.time_series.values) == [1.0, 2.0, 3.0]


_SITE = SiteID("mysite")
_SERVICE = Service(site_id=_SITE, host_name=HostName("h"), service_name=ServiceName("svc"))
_SPEC = TemplateGraphSpecification(site=None, host_name=HostAddress("h"), service_description="svc")
_RANGE = TimeRange(start=0, end=30, step=10)
# The check the translation under test is registered for, as the plug-in names it and as the
# performance data of a passive check spells it.
_CHECK_PLUGIN = "foo"

type _MetricTranslations = Mapping[
    str, translations.RenameTo | translations.ScaleBy | translations.RenameToAndScaleBy
]


@dataclass
class _FakeMetricNames:
    metric_name: str

    def __call__(self) -> Mapping[Service, frozenset[MetricName]]:
        return {_SERVICE: frozenset({MetricName(self.metric_name)})}


@dataclass
class _FakeRRDFetchPerformanceData:
    # In place of RRDFetchPerformanceData: the performance data every requested service carries.
    perf_data: str

    def __call__(
        self, services: Sequence[Service], *, only_site: SiteID | None
    ) -> Sequence[PerformanceDataRow]:
        return [
            PerformanceDataRow(
                service=service,
                site_id=_SITE,
                perf_data=self.perf_data,
                check_command=f"check_mk-{_CHECK_PLUGIN}",
            )
            for service in services
        ]


@dataclass
class _FakeRRDFetchTimeSeries:
    # In place of RRDFetchTimeSeries: the RRDs behind a service, keyed by the column they are read
    # from. Records which columns a series was asked for.
    columns: Mapping[str, Sequence[float | None]]
    requested: list[str] = field(default_factory=list)

    def __call__(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
        only_site: SiteID | None,
    ) -> Mapping[RRDMetric, TimeSeries]:
        self.requested += [str(metric.metric_name) for metric in rrd_metrics]
        return {
            metric: TimeSeries(time_range=time_range, values=values)
            for metric in rrd_metrics
            if (values := self.columns.get(str(metric.metric_name))) is not None
        }


def _drawn_curves(evaluated: EvaluatedGraph) -> Sequence[EvaluatedCurve]:
    return [
        *(member for stack in evaluated.stacks for member in stack.members),
        *(line.curve for line in evaluated.lines),
    ]


def _drawn(
    metric_name: str,
    perf_data: str,
    columns: Mapping[str, Sequence[float | None]],
    metric_translations: _MetricTranslations,
) -> tuple[EvaluatedCurve, Sequence[str]]:
    # The graph a service's metric is discovered into, evaluated over the data the sources serve:
    # what a user ends up seeing, and the columns the fetch read it from.
    time_series = _FakeRRDFetchTimeSeries(columns)
    [built] = build_template_graphs(
        _SPEC,
        registered_graphs=[],
        registered_metrics={},
        fetch_metric_names=_FakeMetricNames(metric_name),
    )
    [evaluated] = _EvaluateTemplateGraphs(
        CommonGraphOptions(consolidation_function=ConsolidationFunction.MAX, time_range=_RANGE),
        EngineRRDFetchData(
            debug=True,
            registered_translations=[
                translations.Translation(
                    name="t",
                    check_commands=[translations.PassiveCheck(_CHECK_PLUGIN)],
                    translations=metric_translations,
                )
            ],
            performance_data_source=_FakeRRDFetchPerformanceData(perf_data),
            time_series_source=time_series,
        ),
    )(built.graph).graphs
    [curve] = _drawn_curves(evaluated)
    return curve, time_series.requested


def test_a_scaling_translation_draws_the_series_in_the_translated_unit() -> None:
    # A translation that only scales leaves the column name untouched, so the series is read from the
    # metric's own column - but it still has to carry the factor, exactly as the value and the
    # thresholds do. Legacy applies it to the series as well (via the RPN of the rrddata column).
    curve, requested = _drawn(
        "x", "x=5;7;9", {"x": [1.0, 2.0, 3.0]}, {"x": translations.ScaleBy(1024)}
    )
    assert requested == ["x"]
    assert curve.value == 5120.0
    assert list(curve.time_series.values) == [1024.0, 2048.0, 3072.0]


def test_a_renaming_translation_draws_the_old_column_scaled() -> None:
    # The canonical metric has no column of its own here: the series comes from the column the perf
    # data actually carried, scaled by the translation's factor.
    curve, requested = _drawn(
        "new",
        "old=5",
        {"old": [1.0, 2.0, 3.0]},
        {"old": translations.RenameToAndScaleBy("new", 1000)},
    )
    assert requested == ["old"]
    assert curve.value == 5000.0
    assert list(curve.time_series.values) == [1000.0, 2000.0, 3000.0]


def test_two_columns_translated_to_one_metric_are_drawn_as_one_curve() -> None:
    # Two perf data columns renamed onto one metric contribute one series each - which reading the
    # canonical column alone could not - merged point-wise, the first column with a value winning.
    curve, requested = _drawn(
        "m",
        "a=1 b=2",
        {"a": [None, 2.0, None], "b": [9.0, 9.0, 9.0]},
        {"a": translations.RenameTo("m"), "b": translations.RenameTo("m")},
    )
    assert requested == ["a", "b"]
    assert list(curve.time_series.values) == [9.0, 2.0, 9.0]


def test_a_deprecated_column_absent_from_the_perf_data_is_still_drawn() -> None:
    # The old column is gone from the perf data but its RRD is still around, so it is read alongside
    # the current one - with the factor of the translation that renamed it, while the current column
    # stays unscaled.
    curve, requested = _drawn(
        "new",
        "new=5",
        {"new": [None, None, 3.0], "old": [1.0, 2.0, None]},
        {"old": translations.RenameToAndScaleBy("new", 1000)},
    )
    assert requested == ["new", "old"]
    assert curve.value == 5.0
    assert list(curve.time_series.values) == [1000.0, 2000.0, 3.0]


def test_a_metric_without_perf_data_is_drawn_from_its_own_column_unscaled() -> None:
    # No perf data entry means no translation was applied to this metric, so its own column is read
    # as it is - and with no value, only the series is drawn.
    curve, requested = _drawn("y", "x=5", {"y": [1.0, 2.0, 3.0]}, {"x": translations.ScaleBy(1024)})
    assert requested == ["y"]
    assert curve.value is None
    assert list(curve.time_series.values) == [1.0, 2.0, 3.0]
