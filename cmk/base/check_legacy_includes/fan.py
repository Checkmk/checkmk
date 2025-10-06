#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyResult


# migrated to cmk.plugins.lib/fan.py
def check_fan(rpm: float, params: Mapping[str, Any] | tuple[float, float]) -> LegacyResult:
    if isinstance(params, Mapping):
        param_dict = params
    else:
        param_dict = {"lower": params}

    levels = param_dict.get("upper", (None, None)) + param_dict.get("lower", (None, None))
    return check_levels(
        rpm,
        "fan" if param_dict.get("output_metrics") else None,
        levels,
        human_readable_func=lambda x: f"{int(x)} RPM",
        infoname="Speed",
    )
