#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.legacy.v0_unstable import check_levels


# migrated to cmk.plugins.lib/fan.py
def check_fan(rpm, params):
    if isinstance(params, tuple):
        params = {"lower": params}

    levels = params.get("upper", (None, None)) + params.get("lower", (None, None))
    return check_levels(
        rpm,
        "fan" if params.get("output_metrics") else None,
        levels,
        unit="RPM",
        human_readable_func=int,
        infoname="Speed",
    )
