#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final, NewType, Self

from ._options import TimeRange

HostName = NewType("HostName", str)
ServiceName = NewType("ServiceName", str)
SiteID = NewType("SiteID", str)


class MetricName(str):
    # A metric name normalised to PNP4Nagios format: a str subclass whose construction is a projection
    # (non-injective). The raw name is pnp-cleaned, so a name carrying spaces / ":" / "/" / "\" / NUL is
    # mapped to its canonical RRD identifier.
    def __new__(cls, text: str) -> Self:
        # An embedded null byte is mapped to "_" like the other path-hostile chars: it would otherwise
        # make open() raise "ValueError: embedded null byte" when the RRD is created.
        return super().__new__(
            cls,
            text.replace(" ", "_")
            .replace(":", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace("\x00", "_"),
        )


@dataclass(frozen=True, kw_only=True)
class Service:
    # The monitoring site the service lives on, when known. Carried through matching so the metrics
    # built for the service can be tagged with it; None means "site not (yet) known".
    site_id: SiteID | None = None
    host_name: HostName
    service_name: ServiceName


@dataclass(frozen=True, kw_only=True)
class PerformanceData:
    value: float | None
    lower_warning: float | None = None
    lower_critical: float | None = None
    warning: float | None = None
    critical: float | None = None
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True, kw_only=True)
class TimeSeries:
    time_range: TimeRange
    values: Sequence[float | None]


def _num_points(time_range: TimeRange) -> int:
    if time_range.step <= 0:
        return 0
    return max(0, (time_range.end - time_range.start) // time_range.step)


def constant_time_series(value: float | None, time_range: TimeRange) -> TimeSeries:
    # The same value at every point of the range - the shape a quantity without a fetched series of
    # its own draws on: a constant, a threshold, or a present-but-all-None curve.
    return TimeSeries(time_range=time_range, values=[value] * _num_points(time_range))


# The one macro spelling the engine itself knows: a macro-less title fanned into several series
# falls back to appending this macro's value so the curves stay distinguishable.
MACRO_SERIES_ID: Final = "$SERIES_ID$"


@dataclass(frozen=True, kw_only=True)
class FetchedData:
    performance_data: PerformanceData | None
    time_series: TimeSeries | None
    # Per-series title macros carried by a fan-out leaf's series (empty for a single, non-fanned
    # series). The fetch layer names them (e.g. $HOST_NAME$, MACRO_SERIES_ID); the engine only
    # substitutes whatever it is handed into the curve title.
    label_macros: Mapping[str, str] = field(default_factory=dict)
