#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckResult, Metric, render

_Levels = tuple[float, float]


def check_dhcp_pools_levels(
    free: float | None,
    used: float | None,
    pending: float | None,
    size: float,
    params: Mapping[str, Any],
) -> CheckResult:
    for category, value in [("free", free), ("used", used), ("pending", pending)]:
        if value is None:
            continue

        value_abs = value
        value_perc = float(value) / size * 100.0 if size else 0.0

        levels_abs: _Levels | None = None
        levels_perc: _Levels | None = None
        metric_levels: _Levels | None = None
        if (levels := params.get(f"{category}_leases")) is not None:
            if isinstance(levels[0], float):  # here we have levels in percent
                levels_perc = levels
                metric_levels = levels[0] / 100.0 * size, levels[1] / 100.0 * size
            else:
                levels_abs = levels
                metric_levels = levels

        yield from check_levels_v1(
            value_abs,
            levels_lower=levels_abs,
            render_func=lambda x: str(int(x)),
            label=f"{category.capitalize()} leases",
        )
        yield from check_levels_v1(
            value_perc,
            levels_lower=levels_perc,
            render_func=render.percent,
        )
        yield Metric(
            f"{category}_dhcp_leases", value_abs, levels=metric_levels, boundaries=(0, size)
        )
