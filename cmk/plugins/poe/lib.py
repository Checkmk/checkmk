#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v2 import check_levels, CheckResult, render, Result, State

poe_default_levels = ("fixed", (90.0, 95.0))


#  constants for operational status of poe interface
class PoeStatus(int, enum.Enum):
    ON = 1
    OFF = 2
    FAULTY = 3


# PoE data
class PoeValues(NamedTuple):
    poe_max: float
    poe_used: float
    poe_status: PoeStatus
    poe_status_detail: str | None


def check_poe_data(params: Mapping[str, Any], poe_data: PoeValues) -> CheckResult:
    # data sanity-check
    if poe_data.poe_max < 0 or poe_data.poe_used < 0 or poe_data.poe_status not in range(1, 4):
        yield Result(
            state=State.UNKNOWN,
            summary=f"Device returned faulty data: nominal power: {poe_data.poe_max}, power consumption: {poe_data.poe_used}, operational status: {poe_data.poe_status}",
        )
        return

    # PoE on device is turned ON
    if poe_data.poe_status == PoeStatus.ON:
        # calculate percentage of power consumption
        poe_used_percentage = (
            ((float(poe_data.poe_used) / float(poe_data.poe_max)) * 100)
            if poe_data.poe_max > 0
            else 0
        )

        yield from check_levels(
            poe_used_percentage,
            metric_name="power_usage_percentage",
            levels_upper=params.get("levels", poe_default_levels),
            render_func=render.percent,
            label=f"POE usage ({poe_data.poe_used}W/{poe_data.poe_max}W): ",
        )
        return

    # PoE on device is turned OFF
    if poe_data.poe_status == PoeStatus.OFF:
        yield Result(state=State.OK, summary="Operational status of the PSE is OFF")
        return

    # PoE on device is FAULTY
    if poe_data.poe_status == PoeStatus.FAULTY:
        fault_detail = ""
        if poe_data.poe_status_detail:
            # optionally concat fault detail string
            fault_detail = " (%s)" % poe_data.poe_status_detail

        yield Result(
            state=State.CRIT, summary=f"Operational status of the PSE is FAULTY{fault_detail}"
        )
        return
