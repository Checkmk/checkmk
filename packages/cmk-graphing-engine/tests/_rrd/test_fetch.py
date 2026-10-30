#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.graphing_engine import (
    ConsolidationFunction,
    HostName,
    MetricName,
    RRDMetric,
    ServiceName,
    SiteID,
    time_series_of_rrd_column,
    TimeRange,
    TimeSeries,
    TimeSeriesWithEdgeNeighbours,
    timestamps,
)
from tests._fixtures import (
    _DAY,
    _FakeRRDWithOneArchive,
    _FIVE_MINUTES,
    _HALF_HOUR_A_WEEK_AGO,
    _NOW,
)


def test_a_column_reads_its_grid_from_the_header() -> None:
    assert time_series_of_rrd_column([0.0, 120.0, 60.0, 1.0, None]) == TimeSeries(
        time_range=TimeRange(start=0, end=120, step=60), values=[1.0, None]
    )


def test_a_column_without_values_holds_no_series() -> None:
    assert time_series_of_rrd_column([0.0, 120.0, 60.0]) is None


def test_a_column_with_a_gap_in_its_header_is_refused() -> None:
    with pytest.raises(ValueError):
        time_series_of_rrd_column([0.0, None, 60.0, 1.0])


_METRIC = RRDMetric(
    site_id=SiteID("mysite"),
    host_name=HostName("h"),
    service_name=ServiceName("svc"),
    metric_name=MetricName("x"),
)


def _fetched_with_edge_neighbours(rrd: _FakeRRDWithOneArchive) -> TimeSeries:
    return TimeSeriesWithEdgeNeighbours(rrd, now=_NOW)(
        [_METRIC],
        consolidation_function=ConsolidationFunction.MAX,
        time_range=_HALF_HOUR_A_WEEK_AGO,
        only_site=None,
    )[_METRIC]


@pytest.mark.parametrize(
    "archive_step",
    [
        pytest.param(_FIVE_MINUTES, id="the default archive"),
        pytest.param(_DAY, id="an archive coarser than the default"),
    ],
)
def test_old_data_comes_with_a_sample_before_the_window(archive_step: int) -> None:
    fetched = _fetched_with_edge_neighbours(_FakeRRDWithOneArchive(archive_step=archive_step))
    assert timestamps(fetched.time_range)[0] < _HALF_HOUR_A_WEEK_AGO.start


@pytest.mark.parametrize(
    "archive_step",
    [
        pytest.param(_FIVE_MINUTES, id="the default archive"),
        pytest.param(_DAY, id="an archive coarser than the default"),
    ],
)
def test_old_data_comes_with_a_sample_after_the_window(archive_step: int) -> None:
    fetched = _fetched_with_edge_neighbours(_FakeRRDWithOneArchive(archive_step=archive_step))
    assert timestamps(fetched.time_range)[-1] > _HALF_HOUR_A_WEEK_AGO.end


@pytest.mark.parametrize(
    "archive_step",
    [
        pytest.param(_FIVE_MINUTES, id="the default archive"),
        pytest.param(60, id="an archive finer than the default"),
    ],
)
def test_an_archive_no_coarser_than_expected_is_queried_once(archive_step: int) -> None:
    rrd = _FakeRRDWithOneArchive(archive_step=archive_step)
    _fetched_with_edge_neighbours(rrd)
    assert len(rrd.asked_ranges) == 1


def test_an_archive_coarser_than_expected_is_queried_again() -> None:
    rrd = _FakeRRDWithOneArchive(archive_step=_DAY)
    _fetched_with_edge_neighbours(rrd)
    assert len(rrd.asked_ranges) == 2


def test_the_widened_query_keeps_the_requested_resolution() -> None:
    rrd = _FakeRRDWithOneArchive(archive_step=_FIVE_MINUTES)
    _fetched_with_edge_neighbours(rrd)
    assert [asked.step for asked in rrd.asked_ranges] == [_HALF_HOUR_A_WEEK_AGO.step]
