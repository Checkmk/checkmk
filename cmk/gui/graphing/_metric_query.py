#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, override

from cmk.graphing_engine import TimeSeries

type AttributeGroup = Literal["resource", "scope", "data_point"]


@dataclass(frozen=True, kw_only=True)
class GraphLineGroupByKey:
    kind: AttributeGroup
    key: str


@dataclass(frozen=True, kw_only=True)
class GaugeLast:
    lookback_seconds: float
    type_: Literal["gauge_last"] = "gauge_last"


@dataclass(frozen=True, kw_only=True)
class GaugeMax:
    lookback_seconds: float
    type_: Literal["gauge_max"] = "gauge_max"


@dataclass(frozen=True, kw_only=True)
class GaugeAvg:
    lookback_seconds: float
    type_: Literal["gauge_avg"] = "gauge_avg"


@dataclass(frozen=True, kw_only=True)
class GaugeMin:
    lookback_seconds: float
    type_: Literal["gauge_min"] = "gauge_min"


@dataclass(frozen=True, kw_only=True)
class SumRate:
    lookback_seconds: float
    type_: Literal["sum_rate"] = "sum_rate"


@dataclass(frozen=True, kw_only=True)
class SumLastRaw:
    lookback_seconds: float
    type_: Literal["sum_last_raw"] = "sum_last_raw"


@dataclass(frozen=True, kw_only=True)
class SumDelta:
    lookback_seconds: float
    type_: Literal["sum_delta"] = "sum_delta"


@dataclass(frozen=True, kw_only=True)
class HistogramQuantile:
    lookback_seconds: float
    percentile: float
    type_: Literal["histogram_quantile"] = "histogram_quantile"


@dataclass(frozen=True, kw_only=True)
class HistogramCountDelta:
    lookback_seconds: float
    type_: Literal["histogram_count_delta"] = "histogram_count_delta"


@dataclass(frozen=True, kw_only=True)
class HistogramCountRate:
    lookback_seconds: float
    type_: Literal["histogram_count_rate"] = "histogram_count_rate"


@dataclass(frozen=True, kw_only=True)
class HistogramSumRate:
    lookback_seconds: float
    type_: Literal["histogram_sum_rate"] = "histogram_sum_rate"


@dataclass(frozen=True, kw_only=True)
class HistogramSumDelta:
    lookback_seconds: float
    type_: Literal["histogram_sum_delta"] = "histogram_sum_delta"


@dataclass(frozen=True, kw_only=True)
class HistogramSumRaw:
    lookback_seconds: float
    type_: Literal["histogram_sum_raw"] = "histogram_sum_raw"


@dataclass(frozen=True, kw_only=True)
class HistogramCountRaw:
    lookback_seconds: float
    type_: Literal["histogram_count_raw"] = "histogram_count_raw"


@dataclass(frozen=True, kw_only=True)
class HistogramFractionBelow:
    lookback_seconds: float
    threshold: float
    type_: Literal["histogram_fraction_below"] = "histogram_fraction_below"


@dataclass(frozen=True, kw_only=True)
class HistogramFractionBetween:
    lookback_seconds: float
    lower_threshold: float
    upper_threshold: float
    type_: Literal["histogram_fraction_between"] = "histogram_fraction_between"


@dataclass(frozen=True, kw_only=True)
class HistogramPreserveQuantile:
    lookback_seconds: float
    percentile: float
    group_by: tuple[GraphLineGroupByKey, ...]
    type_: Literal["histogram_preserve_quantile"] = "histogram_preserve_quantile"


@dataclass(frozen=True, kw_only=True)
class HistogramPreserveFractionBelow:
    lookback_seconds: float
    threshold: float
    group_by: tuple[GraphLineGroupByKey, ...]
    type_: Literal["histogram_preserve_fraction_below"] = "histogram_preserve_fraction_below"


@dataclass(frozen=True, kw_only=True)
class HistogramPreserveFractionBetween:
    lookback_seconds: float
    lower_threshold: float
    upper_threshold: float
    group_by: tuple[GraphLineGroupByKey, ...]
    type_: Literal["histogram_preserve_fraction_between"] = "histogram_preserve_fraction_between"


type ConsolidationFunction = (
    GaugeLast
    | GaugeMax
    | GaugeAvg
    | GaugeMin
    | SumRate
    | SumLastRaw
    | SumDelta
    | HistogramQuantile
    | HistogramCountDelta
    | HistogramCountRate
    | HistogramSumRate
    | HistogramSumDelta
    | HistogramSumRaw
    | HistogramCountRaw
    | HistogramFractionBelow
    | HistogramFractionBetween
    | HistogramPreserveQuantile
    | HistogramPreserveFractionBelow
    | HistogramPreserveFractionBetween
)


def canonical_mapping_key(mapping: Mapping[str, object] | None) -> str:
    """Stable, hashable identity for an (optional) wire mapping such as an attribute
    filter or a group-by aggregator."""
    return json.dumps(mapping, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class QueryDataKey:
    metric_name: str
    consolidation_function: ConsolidationFunction
    attribute_filter: Mapping[str, object]
    aggregator: Mapping[str, object] | None = None

    @override
    def __hash__(self) -> int:
        # The filter mapping is unhashable, so identity comes from its canonical serialization.
        return hash(
            (
                self.metric_name,
                self.consolidation_function,
                canonical_mapping_key(self.attribute_filter),
                canonical_mapping_key(self.aggregator),
            )
        )


@dataclass(frozen=True)
class QueryDataTimeSeries:
    time_series: TimeSeries
    id: str
    attributes: Mapping[AttributeGroup, Mapping[str, str]]


@dataclass(frozen=True, kw_only=True)
class QueryDataLimit:
    max_series_per_query: int
    num_series_per_query: int


@dataclass(frozen=True)
class QueryDataValue:
    time_series: Sequence[QueryDataTimeSeries]
    limit: QueryDataLimit


type QueryData = Mapping[QueryDataKey, QueryDataValue]


@dataclass(frozen=True)
class QueryDataError:
    keys: Sequence[QueryDataKey]
    exception: Exception
