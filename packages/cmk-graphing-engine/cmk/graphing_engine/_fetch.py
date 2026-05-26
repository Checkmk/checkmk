#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from ._objects import MetricName
from ._options import ConsolidationFunction, ServiceRef, TimeRange


@dataclass(frozen=True, kw_only=True)
class Scalars:
    lower_warning: float | None = None
    lower_critical: float | None = None
    warning: float | None = None
    critical: float | None = None
    minimum: float | None = None
    maximum: float | None = None

    def __bool__(self) -> bool:
        return any(
            value is not None
            for value in (
                self.lower_warning,
                self.lower_critical,
                self.warning,
                self.critical,
                self.minimum,
                self.maximum,
            )
        )


@dataclass(frozen=True, kw_only=True)
class RRDKey:
    service: ServiceRef
    metric_name: MetricName
    scale: float


@dataclass(frozen=True, kw_only=True)
class TranslatedMetric:
    name: MetricName
    value: float | None
    bounds: Scalars
    originals: Sequence[RRDKey]


@dataclass(frozen=True, kw_only=True)
class TimeSeries:
    time_range: TimeRange
    values: Sequence[float | None]


class FetchRRD(Protocol):
    def translated_metrics(
        self, services: Sequence[ServiceRef]
    ) -> Mapping[ServiceRef, Mapping[MetricName, TranslatedMetric]]: ...

    def time_series(
        self,
        keys: Sequence[RRDKey],
        *,
        time_range: TimeRange,
        consolidation_function: ConsolidationFunction,
    ) -> Mapping[RRDKey, TimeSeries]: ...
