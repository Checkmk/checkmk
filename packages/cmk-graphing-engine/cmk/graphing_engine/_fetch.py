#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Protocol

from ._fetched import FetchedData
from ._graph import Graph
from ._naming import MetricName, Service
from ._quantities import EvaluationContext, MetricProtocol
from ._timeseries import ConsolidationFunction, TimeRange


class FetchMetricNamesProtocol(Protocol):
    def __call__(self) -> Mapping[Service, frozenset[MetricName]]: ...


class FetchDataProtocol(Protocol):
    def __call__(
        self,
        metrics: Sequence[MetricProtocol],
        *,
        consolidation_function: ConsolidationFunction,
        time_range: TimeRange,
    ) -> Mapping[MetricProtocol, Sequence[FetchedData]]: ...


def fetch_evaluation_context(
    *,
    consolidation_function: ConsolidationFunction,
    time_range: TimeRange,
    graphs: Sequence[Graph],
    fetch_data: FetchDataProtocol,
) -> EvaluationContext:
    metrics = list(dict.fromkeys(metric for graph in graphs for metric in graph.metrics()))
    fetched = fetch_data(
        metrics, consolidation_function=consolidation_function, time_range=time_range
    )
    # The evaluation grid is the one the fetched series actually sit on (the source aligns them to a
    # single grid), not the requested one - the RRD backend may snap start/end/step. Constants and
    # operations are built on this grid so they line up with the fetched data. Falls back to the
    # requested range when nothing was fetched.
    resolved_time_range = next(
        (
            data.time_series.time_range
            for series in fetched.values()
            for data in series
            if data.time_series is not None
        ),
        time_range,
    )
    return EvaluationContext(time_range=resolved_time_range, fetched=fetched)
