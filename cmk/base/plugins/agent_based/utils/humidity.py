#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, List, Mapping, Optional, Tuple, Union

from ..agent_based_api.v1 import check_levels, render, type_defs

CheckParams = Union[
    None, Mapping[str, Any], Optional[List[float]], Tuple[float, float, float, float]
]


def check_humidity(humidity: float, params: CheckParams) -> type_defs.CheckResult:
    levels_upper, levels_lower = None, None
    if isinstance(params, dict):
        levels_upper = params.get("levels") or None
        levels_lower = params.get("levels_lower") or None
    elif isinstance(params, (list, tuple)):
        # old params = (crit_low , warn_low, warn, crit)
        levels_upper = params[2], params[3]
        levels_lower = params[1], params[0]

    yield from check_levels(
        humidity,
        levels_upper=levels_upper,
        levels_lower=levels_lower,
        metric_name="humidity",
        render_func=render.percent,
        boundaries=(0, 100),
    )
