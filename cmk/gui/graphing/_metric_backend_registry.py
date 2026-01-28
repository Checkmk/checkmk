#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from cmk.ccc.plugin_registry import Registry
from cmk.ccc.resulttype import Result
from cmk.ccc.version import Edition

from ._graph_metric_expressions import QueryData, QueryDataError, QueryDataKey


class FetchTimeSeries(Protocol):
    def __call__(
        self,
        keys: Sequence[QueryDataKey],
        *,
        start_time: float,
        end_time: float,
        step: int,
    ) -> Iterator[Result[QueryData, QueryDataError]]: ...


@dataclass(frozen=True, kw_only=True)
class MetricBackend:
    edition: Edition

    def get_time_series_fetcher(self) -> FetchTimeSeries | None:
        return None


class MetricBackendRegistry(Registry[MetricBackend]):
    def plugin_name(self, instance: MetricBackend) -> str:
        return str(instance.edition)


metric_backend_registry = MetricBackendRegistry()
