#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckResult, render

CheckParams = None | Mapping[str, Any] | list[float] | None | tuple[float, float, float, float]


def check_humidity(humidity: float, params: CheckParams) -> CheckResult:
    levels_upper, levels_lower = None, None
    if isinstance(params, dict | Mapping):
        levels_upper = params.get("levels") or None
        levels_lower = params.get("levels_lower") or None
    elif isinstance(params, list | tuple):
        # old params = (crit_low , warn_low, warn, crit)
        levels_upper = params[2], params[3]
        levels_lower = params[1], params[0]

    yield from check_levels_v1(
        humidity,
        levels_upper=levels_upper,
        levels_lower=levels_lower,
        metric_name="humidity",
        render_func=render.percent,
        boundaries=(0, 100),
    )
