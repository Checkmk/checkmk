#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import assert_never, Final

from ._timeseries import TimeSeries


@dataclass(frozen=True, kw_only=True)
class PerformanceData:
    value: float | None
    lower_warning: float | None = None
    lower_critical: float | None = None
    warning: float | None = None
    critical: float | None = None
    minimum: float | None = None
    maximum: float | None = None


class ScalarKind(enum.StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"
    LOWER_WARNING = "lower_warning"
    LOWER_CRITICAL = "lower_critical"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"


def value_of(data: PerformanceData, scalar_kind: ScalarKind) -> float | None:
    match scalar_kind:
        case ScalarKind.WARNING:
            return data.warning
        case ScalarKind.CRITICAL:
            return data.critical
        case ScalarKind.LOWER_WARNING:
            return data.lower_warning
        case ScalarKind.LOWER_CRITICAL:
            return data.lower_critical
        case ScalarKind.MINIMUM:
            return data.minimum
        case ScalarKind.MAXIMUM:
            return data.maximum
        case _:
            assert_never(scalar_kind)


# The one macro spelling the engine itself knows: a macro-less title fanned into several series
# falls back to appending this macro's value so the curves stay distinguishable.
MACRO_SERIES_ID: Final = "$SERIES_ID$"

# The attributes of a fetched series, kind -> name -> value. The kinds are the fetch layer's to name
# (e.g. a metric backend's "resource" / "scope" / "data_point").
type SeriesAttributes = Mapping[str, Mapping[str, str]]


@dataclass(frozen=True, kw_only=True)
class FetchedData:
    performance_data: PerformanceData | None
    time_series: TimeSeries | None
    # Per-series title macros carried by a fan-out leaf's series (empty for a single, non-fanned
    # series). The fetch layer names them (e.g. $HOST_NAME$, MACRO_SERIES_ID); the engine only
    # substitutes whatever it is handed into the curve title.
    label_macros: Mapping[str, str] = field(default_factory=dict)
    # The attributes the fetched series carries, grouped by kind (empty for a series without any).
    # The engine does not interpret them: it hands them to the curve so a consumer can show them.
    series_attributes: SeriesAttributes = field(default_factory=dict)
