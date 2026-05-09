#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checking classes for the v3_unstable API"""

from __future__ import annotations

from dataclasses import dataclass, KW_ONLY


@dataclass(frozen=True)
class Metric:
    """Create a metric for a service

    Args:
        name:         The name of the metric.
                      Empty names or names containing spaces or any of the characters
                      ``:``, ``/`` or ``\\`` will raise an exception.
                      Metrics with names containing ``=`` or ``'`` will silently be dropped.
        value:        The measured value.
        levels:       A pair of upper levels, ie. warn and crit. This information is only used
                      for visualization by the graphing system. It does not affect the service state.
        lower_levels: A pair of lower levels, ie. warn and crit. This information is only used
                      for visualization by the graphing system. It does not affect the service state.
        boundaries:   Additional information on the value domain for the graphing system.

    Example:

        >>> my_metric = Metric("used_slots_percent", 23.0, levels=(80, 90), lower_levels=(5, 1), boundaries=(0, 100))

    """

    name: str
    value: float
    _: KW_ONLY
    levels: tuple[float | None, float | None] = (None, None)
    lower_levels: tuple[float | None, float | None] = (None, None)
    boundaries: tuple[float | None, float | None] = (None, None)

    def __post_init__(self) -> None:
        if not self.name:
            raise TypeError("metric name must not be empty")

        # this is set is chosen such that the metric name would not be changed by `pnp_cleanup`
        if offenders := set(self.name) & {" ", ":", "/", "\\"}:
            raise TypeError(f"invalid character(s) in metric name: {''.join(offenders)!r}")
