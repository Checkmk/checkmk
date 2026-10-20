#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Sequence
from dataclasses import dataclass

from cmk.graphing_engine._data._fetched import ScalarKind, value_of
from cmk.graphing_engine._data._naming import MetricName
from cmk.graphing_engine._data._timeseries import constant_time_series, last_present
from cmk.graphing_engine._quantities._quantity import (
    EvaluatedQuantity,
    EvaluationContext,
    QuantityProtocol,
)

from ._naming import HostName, Service, ServiceName, SiteID


class ConsolidationFunction(enum.StrEnum):
    # How the samples falling into one step of the range collapse into the single point drawn for it.
    MIN = "min"
    MAX = "max"
    AVERAGE = "average"


@dataclass(frozen=True, kw_only=True)
class RRDMetric:
    # The monitoring site the service lives on. None until resolved during the fetch; once known it
    # is part of the metric's identity, so the same host/service on two sites are distinct curves.
    site_id: SiteID | None = None
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    consolidation_function: ConsolidationFunction | None = None

    def kind(self) -> str:
        return "rrd_metric"

    def ident(self) -> str:
        location = "" if self.site_id is None else f"{self.site_id}/"
        return f"{self.kind()}({location}{self.host_name}/{self.service_name}/{self.metric_name})"

    def service(self) -> Service:
        return Service(
            site_id=self.site_id,
            host_name=self.host_name,
            service_name=self.service_name,
        )

    def children(self) -> Sequence[QuantityProtocol]:
        return ()

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        data = context.data_of(self)
        value = None if data is None else data.value
        existing = context.time_series_of(self)
        if value is None and existing is None:
            return []
        return [
            EvaluatedQuantity(
                value=value,
                time_series=(
                    existing
                    if existing is not None
                    else constant_time_series(None, context.time_range)
                ),
            )
        ]


class PredictionCurveKind(enum.StrEnum):
    UPPER_REFERENCE = "upper_reference"
    UPPER_WARNING = "upper_warning"
    UPPER_CRITICAL = "upper_critical"
    LOWER_REFERENCE = "lower_reference"
    LOWER_WARNING = "lower_warning"
    LOWER_CRITICAL = "lower_critical"


@dataclass(frozen=True, kw_only=True)
class PredictionMetric:
    site_id: SiteID
    host_name: HostName
    service_name: ServiceName
    metric_name: MetricName
    period: str
    valid_from: int
    valid_until: int
    curve_kind: PredictionCurveKind

    def kind(self) -> str:
        return "prediction_metric"

    def ident(self) -> str:
        return (
            f"{self.kind()}({self.site_id}/{self.host_name}/{self.service_name}/{self.metric_name}"
            f",{self.period},{self.valid_from},{self.valid_until},{self.curve_kind})"
        )

    def children(self) -> Sequence[QuantityProtocol]:
        return ()

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        if (time_series := context.time_series_of(self)) is None:
            return []
        return [
            EvaluatedQuantity(
                value=last_present(time_series.values),
                time_series=time_series,
            )
        ]


def rrd_metric_of(service: Service, metric_name: str) -> RRDMetric:
    return RRDMetric(
        site_id=service.site_id,
        host_name=service.host_name,
        service_name=service.service_name,
        metric_name=MetricName(metric_name),
    )


@dataclass(frozen=True)
class ScalarOf:
    metric: RRDMetric
    scalar_kind: ScalarKind

    def kind(self) -> str:
        return "scalar_of"

    def ident(self) -> str:
        return f"{self.kind()}({self.scalar_kind},{self.metric.ident()})"

    def children(self) -> Sequence[QuantityProtocol]:
        return (self.metric,)

    def evaluate(self, context: EvaluationContext) -> Sequence[EvaluatedQuantity]:
        if (data := context.data_of(self.metric)) is None:
            return []
        value = value_of(data, self.scalar_kind)
        return [
            EvaluatedQuantity(
                value=value, time_series=constant_time_series(value, context.time_range)
            )
        ]
