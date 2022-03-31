#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping

from ..agent_based_api.v1 import check_levels, render
from ..agent_based_api.v1.type_defs import CheckResult


def check_cache_hitratio(hitratio: float, params: Mapping[str, Any]) -> CheckResult:
    """
    check function for redis cache hitratio. To be used in conjuction with the
    redis_hitratio rulespec.

    Params:
    hitratio: ratio of successful cache hits, value between 0 and 1
    params: dict expecting two keys, levels_upper_hitratio and levels_lower_hitratio.
    """
    hitratio *= 100
    levels_upper = params["levels_upper_hitratio"]
    levels_lower = params["levels_lower_hitratio"]
    yield from check_levels(
        hitratio,
        levels_upper=levels_upper,
        levels_lower=levels_lower,
        metric_name="hitratio",
        render_func=render.percent,
        label="Hitratio",
    )
