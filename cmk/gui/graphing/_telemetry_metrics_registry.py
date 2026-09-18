#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import override, Protocol

from cmk.ccc.plugin_registry import Registry
from cmk.ccc.resulttype import Result
from cmk.graphing_engine import QuantityProtocol

from ._metric_query import (
    ConsolidationFunction,
    QueryData,
    QueryDataError,
    QueryDataKey,
)

TELEMETRY_METRICS_KEY = "metric_backend"


class FetchTimeSeriesProtocol(Protocol):
    def __call__(
        self,
        keys: Sequence[QueryDataKey],
        *,
        start_time: float,
        end_time: float,
        step: int,
    ) -> Iterator[Result[QueryData, QueryDataError]]: ...


class BackendQueryBuilderProtocol(Protocol):
    """Builds the graph-engine quantity for a metric-backend V2 data source."""

    def __call__(
        self,
        *,
        metric_name: str,
        attribute_filter: Mapping[str, object],
        consolidation_function: ConsolidationFunction,
        aggregator: Mapping[str, object] | None = None,
    ) -> QuantityProtocol: ...


@dataclass(frozen=True, kw_only=True)
class TelemetryMetricsBackend:
    @property
    def feature_available(self) -> bool:
        return False

    def get_time_series_fetcher(self) -> FetchTimeSeriesProtocol | None:
        return None

    def get_backend_query_builder(self) -> BackendQueryBuilderProtocol | None:
        return None


class TelemetryMetricsBackendRegistry(Registry[TelemetryMetricsBackend]):
    @override
    def plugin_name(self, instance: TelemetryMetricsBackend) -> str:
        return TELEMETRY_METRICS_KEY


telemetry_metrics_backend_registry = TelemetryMetricsBackendRegistry()
