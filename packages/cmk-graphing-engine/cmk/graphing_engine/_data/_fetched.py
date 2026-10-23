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


MACRO_SERIES_ID: Final = "$SERIES_ID$"

type SeriesAttributes = Mapping[str, Mapping[str, str]]


@dataclass(frozen=True, kw_only=True)
class FetchedData:
    performance_data: PerformanceData | None
    time_series: TimeSeries | None
    label_macros: Mapping[str, str] = field(default_factory=dict)
    series_attributes: SeriesAttributes = field(default_factory=dict)
