#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import CheckResult, render


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
    yield from check_levels_v1(
        hitratio,
        levels_upper=levels_upper,
        levels_lower=levels_lower,
        metric_name="hitratio",
        render_func=render.percent,
        label="Hitratio",
    )


def check_clients_connected(connected_clients: float, params: Mapping[str, Any]) -> CheckResult:
    levels_upper = params["clients_connected"]
    yield from check_levels_v1(
        connected_clients,
        levels_upper=levels_upper,
        metric_name="clients_connected",
        label="Connected Clients",
    )
