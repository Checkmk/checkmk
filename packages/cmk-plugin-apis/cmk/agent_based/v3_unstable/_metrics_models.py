#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The data model of agent sections produced by the telemetry metrics fetcher.

The fetcher serializes :class:`MetricsRecord` instances into the agent
output (one JSON document per line), and the check engine deserializes them
again before passing them to the parse function of a
:class:`MetricsSection`.
"""

from collections.abc import Mapping, Sequence
from enum import Enum, StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class AggregationTemporality(Enum):
    UNSPECIFIED = 0
    DELTA = 1
    CUMULATIVE = 2


class MetricType(StrEnum):
    GAUGE = "gauge"
    SUM = "sum"
    HISTOGRAM = "histogram"
    EXPONENTIAL_HISTOGRAM = "exponential_histogram"
    SUMMARY = "summary"


class CustomMetricMeta(BaseModel, frozen=True):
    series_id: str
    metric_type: MetricType
    name: str
    description: str
    resource_attributes: Mapping[str, str]
    scope_name: str
    scope_version: str
    scope_attributes: Mapping[str, str]
    attributes: Mapping[str, str]
    unit: str
    aggregation_temporality: AggregationTemporality = AggregationTemporality.UNSPECIFIED
    is_monotonic: bool | None = None


class AggregatedInstantGauge(BaseModel, frozen=True):
    type: Literal["gauge"] = "gauge"
    series_id: str
    value: float


class AggregatedInstantSum(BaseModel, frozen=True):
    type: Literal["sum"] = "sum"
    series_id: str
    value_delta: float
    rate: float


class AggregatedInstantHistogram(BaseModel, frozen=True):
    type: Literal["histogram"] = "histogram"
    series_id: str
    count_delta: int
    count_rate: float
    sum_delta: float
    values_at_quantiles: Sequence[float] | None


class MetricsRecord(BaseModel, frozen=True):
    filter_name: str
    metadata: CustomMetricMeta
    data: Annotated[
        AggregatedInstantGauge | AggregatedInstantSum | AggregatedInstantHistogram,
        Field(discriminator="type"),
    ]
