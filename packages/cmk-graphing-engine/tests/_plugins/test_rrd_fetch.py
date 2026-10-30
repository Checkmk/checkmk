#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from cmk.graphing.v1 import translations
from cmk.graphing_engine import (
    ConsolidationFunction,
    FetchedData,
    FetchRRDTimeSeriesProtocol,
    HostName,
    MetricName,
    PerformanceDataRow,
    RRDFetchData,
    RRDMetric,
    Service,
    ServiceName,
    SiteID,
    TimeRange,
    TimeSeries,
    TimeSeriesWithEdgeNeighbours,
)
from tests._fixtures import (
    _DAY,
    _FakeRRDWithOneArchive,
    _FIVE_MINUTES,
    _HALF_HOUR_A_WEEK_AGO,
    _NOW,
)

_LOGGER = logging.getLogger(__name__)
_SITE = SiteID("mysite")
_RANGE = TimeRange(start=0, end=30, step=10)
_CHECK_PLUGIN = "foo"

type _MetricTranslations = Mapping[
    str, translations.RenameTo | translations.ScaleBy | translations.RenameToAndScaleBy
]


def _metric(name: str) -> RRDMetric:
    return RRDMetric(
        site_id=_SITE,
        host_name=HostName("h"),
        service_name=ServiceName("svc"),
        metric_name=MetricName(name),
    )


@dataclass
class _FakePerformanceDataRows:
    perf_data: str
    reads: int = 0

    def __call__(
        self,
        services: Sequence[Service],
        *,
        only_site: SiteID | None,  # noqa: ARG002
    ) -> Sequence[PerformanceDataRow]:
        self.reads += 1
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
class _FakeRRDColumns:
    columns: Mapping[str, Sequence[float | None]]
    requested: list[str] = field(default_factory=list)

    def __call__(
        self,
        rrd_metrics: Sequence[RRDMetric],
        *,
        consolidation_function: ConsolidationFunction,  # noqa: ARG002
        time_range: TimeRange,
        only_site: SiteID | None,  # noqa: ARG002
    ) -> Mapping[RRDMetric, TimeSeries]:
        self.requested += [str(metric.metric_name) for metric in rrd_metrics]
        return {
            metric: TimeSeries(time_range=time_range, values=values)
            for metric in rrd_metrics
            if (values := self.columns.get(str(metric.metric_name))) is not None
        }


def _fetch_data(
    performance_data: _FakePerformanceDataRows,
    time_series: FetchRRDTimeSeriesProtocol,
    *,
    metric_translations: _MetricTranslations | None = None,
    now: float = _NOW,
) -> RRDFetchData:
    return RRDFetchData(
        consolidation_function=ConsolidationFunction.MAX,
        registered_translations=[
            translations.Translation(
                name="t",
                check_commands=[translations.PassiveCheck(_CHECK_PLUGIN)],
                translations=metric_translations,
            )
        ]
        if metric_translations
        else (),
        performance_data_source=performance_data,
        time_series_source=time_series,
        now=now,
        debug=True,
        logger=_LOGGER,
    )


def _fetched(
    metric_name: str,
    perf_data: str,
    columns: _FakeRRDColumns,
    metric_translations: _MetricTranslations,
) -> FetchedData:
    metric = _metric(metric_name)
    [fetched] = _fetch_data(
        _FakePerformanceDataRows(perf_data), columns, metric_translations=metric_translations
    )([metric], time_range=_RANGE)[metric]
    return fetched


def _values(fetched: FetchedData) -> Sequence[float | None]:
    return [] if fetched.time_series is None else list(fetched.time_series.values)


def test_a_scaling_translation_reads_the_metrics_own_column() -> None:
    columns = _FakeRRDColumns({"x": [1.0, 2.0, 3.0]})
    _fetched("x", "x=5;7;9", columns, {"x": translations.ScaleBy(1024)})
    assert columns.requested == ["x"]


def test_a_scaling_translation_scales_the_value() -> None:
    fetched = _fetched(
        "x", "x=5;7;9", _FakeRRDColumns({"x": [1.0, 2.0, 3.0]}), {"x": translations.ScaleBy(1024)}
    )
    assert fetched.performance_data is not None and fetched.performance_data.value == 5120.0


def test_a_scaling_translation_scales_the_series() -> None:
    fetched = _fetched(
        "x", "x=5;7;9", _FakeRRDColumns({"x": [1.0, 2.0, 3.0]}), {"x": translations.ScaleBy(1024)}
    )
    assert _values(fetched) == [1024.0, 2048.0, 3072.0]


def test_a_renaming_translation_reads_the_old_column_scaled() -> None:
    fetched = _fetched(
        "new",
        "old=5",
        _FakeRRDColumns({"old": [1.0, 2.0, 3.0]}),
        {"old": translations.RenameToAndScaleBy("new", 1000)},
    )
    assert _values(fetched) == [1000.0, 2000.0, 3000.0]


def test_two_columns_translated_to_one_metric_merge_into_one_series() -> None:
    fetched = _fetched(
        "m",
        "a=1 b=2",
        _FakeRRDColumns({"a": [None, 2.0, None], "b": [9.0, 9.0, 9.0]}),
        {"a": translations.RenameTo("m"), "b": translations.RenameTo("m")},
    )
    assert _values(fetched) == [9.0, 2.0, 9.0]


def test_a_deprecated_column_absent_from_the_perf_data_is_still_read() -> None:
    fetched = _fetched(
        "new",
        "new=5",
        _FakeRRDColumns({"new": [None, None, 3.0], "old": [1.0, 2.0, None]}),
        {"old": translations.RenameToAndScaleBy("new", 1000)},
    )
    assert _values(fetched) == [1000.0, 2000.0, 3.0]


def test_a_metric_without_perf_data_is_read_from_its_own_column_unscaled() -> None:
    fetched = _fetched(
        "y", "x=5", _FakeRRDColumns({"y": [1.0, 2.0, 3.0]}), {"x": translations.ScaleBy(1024)}
    )
    assert _values(fetched) == [1.0, 2.0, 3.0]


def _fetched_series_ending_at(
    end: int, columns: Mapping[str, Sequence[float | None]], *, now: float
) -> Mapping[str, TimeSeries | None]:
    metrics = [_metric(name) for name in columns]
    fetched = _fetch_data(_FakePerformanceDataRows("x=5"), _FakeRRDColumns(columns), now=now)(
        metrics, time_range=TimeRange(start=end - 30, end=end, step=10)
    )
    return {
        str(metric.metric_name): data.time_series
        for metric in metrics
        for data in fetched.get(metric, ())
    }


def test_the_empty_trailing_step_of_a_range_ending_now_is_dropped() -> None:
    fetched = _fetched_series_ending_at(1000, {"x": [1.0, 2.0, None]}, now=1000.0)
    assert fetched["x"] == TimeSeries(
        time_range=TimeRange(start=970, end=990, step=10), values=[1.0, 2.0]
    )


def test_a_trailing_gap_in_the_past_is_kept() -> None:
    fetched = _fetched_series_ending_at(1000, {"x": [1.0, 2.0, None]}, now=5000.0)
    assert fetched["x"] == TimeSeries(
        time_range=TimeRange(start=970, end=1000, step=10), values=[1.0, 2.0, None]
    )


def test_a_trailing_step_one_series_still_has_data_for_is_kept() -> None:
    fetched = _fetched_series_ending_at(
        1000, {"x": [1.0, 2.0, None], "y": [1.0, 2.0, 3.0]}, now=1000.0
    )
    assert fetched["x"] == TimeSeries(
        time_range=TimeRange(start=970, end=1000, step=10), values=[1.0, 2.0, None]
    )


def test_the_performance_data_is_read_once_when_the_rrd_is_queried_again() -> None:
    performance_data = _FakePerformanceDataRows("x=5")
    _fetch_data(
        performance_data,
        TimeSeriesWithEdgeNeighbours(_FakeRRDWithOneArchive(archive_step=_DAY), now=_NOW),
    )([_metric("x")], time_range=_HALF_HOUR_A_WEEK_AGO)
    assert performance_data.reads == 1


def test_a_fetch_without_edge_neighbours_asks_for_exactly_the_range() -> None:
    rrd = _FakeRRDWithOneArchive(archive_step=_FIVE_MINUTES)
    _fetch_data(_FakePerformanceDataRows("x=5"), rrd)(
        [_metric("x")], time_range=_HALF_HOUR_A_WEEK_AGO
    )
    assert rrd.asked_ranges == [_HALF_HOUR_A_WEEK_AGO]
