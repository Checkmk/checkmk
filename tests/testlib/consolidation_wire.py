#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Build the shared ``consolidation_function`` REST wire for tests.

Build every payload from shared typing, so the openapi unit tests and
the system tests cannot silently drift apart when the wire changes.
"""

from collections.abc import Sequence
from dataclasses import asdict

from cmk.shared_typing.consolidation import (
    ConsolidationGauge,
    ConsolidationGroupByKey,
    ConsolidationHistogramFractionBetween,
    ConsolidationHistogramPreserveFractionBetween,
    ConsolidationHistogramQuantile,
    GaugeFunction,
)


def gauge(function: GaugeFunction, *, lookback_seconds: float) -> dict[str, object]:
    return asdict(
        ConsolidationGauge(type="gauge", function=function, lookback_seconds=lookback_seconds)
    )


def histogram_quantile(*, lookback_seconds: float, percentile: float) -> dict[str, object]:
    return asdict(
        ConsolidationHistogramQuantile(
            type="histogram",
            function="histogram_quantile",
            lookback_seconds=lookback_seconds,
            percentile=percentile,
        )
    )


def histogram_fraction_between(
    *, lookback_seconds: float, lower_threshold: float, upper_threshold: float
) -> dict[str, object]:
    return asdict(
        ConsolidationHistogramFractionBetween(
            type="histogram",
            function="histogram_fraction_between",
            lookback_seconds=lookback_seconds,
            lower_threshold=lower_threshold,
            upper_threshold=upper_threshold,
        )
    )


def histogram_preserve_fraction_between(
    *,
    lookback_seconds: float,
    lower_threshold: float,
    upper_threshold: float,
    group_by: Sequence[ConsolidationGroupByKey] = (),
) -> dict[str, object]:
    return asdict(
        ConsolidationHistogramPreserveFractionBetween(
            type="histogram",
            function="histogram_preserve_fraction_between",
            lookback_seconds=lookback_seconds,
            lower_threshold=lower_threshold,
            upper_threshold=upper_threshold,
            group_by=group_by,
        )
    )
