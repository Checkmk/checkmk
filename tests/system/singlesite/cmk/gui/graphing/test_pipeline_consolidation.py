#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Data pipeline: RRD consolidation functions (R1.1 Area 2).

P-01 and P-02 both query a window older than 48h, so RRDtool serves it from a consolidated
archive rather than the raw one - only then do the three consolidation functions differ, and
only then does a gap have to survive being averaged over.
"""

from collections.abc import Iterator, Mapping, Sequence
from typing import NamedTuple

import pytest

from tests.testlib.graphing import (
    data_points_of_every_metric,
    GraphDataShape,
    injected_ping_rrds,
    InjectedPingRrd,
    ping_graph_internal,
)
from tests.testlib.openapi_session import Consolidation
from tests.testlib.site import Site

pytestmark = pytest.mark.skip_if_edition("community")

_OSCILLATING_HOST = "graph-cf-oscillating"
_GAPS_HOST = "graph-cf-gaps"

_HOUR = 3600


@pytest.fixture(name="injected_rrds", scope="module")
def fixture_injected_rrds(site: Site) -> Iterator[dict[str, InjectedPingRrd]]:
    with injected_ping_rrds(
        site,
        {
            _OSCILLATING_HOST: GraphDataShape.OSCILLATING,
            _GAPS_HOST: GraphDataShape.GAPS,
        },
    ) as injected:
        yield injected


def _fetch_points(
    site: Site,
    internal: Mapping[str, object],
    window: dict[str, int],
    consolidation_function: Consolidation,
) -> Sequence[float | None]:
    response = site.openapi.graph.fetch_data(internal, window, consolidation_function)
    return [value for points in data_points_of_every_metric(response) for value in points]


class _Bucket(NamedTuple):
    minimum: float
    average: float
    maximum: float


def _consolidated_buckets(
    site: Site, internal: Mapping[str, object], window: dict[str, int]
) -> Sequence[_Bucket]:
    minima = _fetch_points(site, internal, window, "min")
    averages = _fetch_points(site, internal, window, "avg")
    maxima = _fetch_points(site, internal, window, "max")
    return [
        _Bucket(minimum=minimum, average=average, maximum=maximum)
        for minimum, average, maximum in zip(minima, averages, maxima, strict=True)
        if minimum is not None and average is not None and maximum is not None
    ]


def test_consolidation_functions_yield_distinct_non_empty_series(
    site: Site, injected_rrds: dict[str, InjectedPingRrd]
) -> None:
    injected = injected_rrds[_OSCILLATING_HOST]
    internal = ping_graph_internal(site, injected.host_name)
    window = injected.window(offset_seconds=24 * _HOUR, length_seconds=6 * _HOUR)

    buckets = _consolidated_buckets(site, internal, window)

    assert buckets, "No bucket holds a value under all three consolidation functions"
    assert all(bucket.minimum <= bucket.average <= bucket.maximum for bucket in buckets), (
        f"A bucket's min/avg/max are out of order: {buckets}"
    )
    assert any(bucket.minimum < bucket.maximum for bucket in buckets), (
        f"No bucket spans a range, so the three functions returned one and the same series:"
        f" {buckets}"
    )


def test_average_consolidation_preserves_gaps(
    site: Site, injected_rrds: dict[str, InjectedPingRrd]
) -> None:
    injected = injected_rrds[_GAPS_HOST]
    internal = ping_graph_internal(site, injected.host_name)
    gap_offset = injected.gap_start - injected.rrd.start

    before_gap = _fetch_points(
        site, internal, injected.window(offset_seconds=_HOUR, length_seconds=6 * _HOUR), "avg"
    )
    inside_gap = _fetch_points(
        site,
        internal,
        injected.window(offset_seconds=gap_offset + 6 * _HOUR, length_seconds=6 * _HOUR),
        "avg",
    )

    assert all(value is not None for value in before_gap), (
        f"Averaging dropped values outside the gap: {before_gap}"
    )
    assert all(value is None for value in inside_gap), (
        f"Averaging filled the gap instead of leaving it null: {inside_gap}"
    )
