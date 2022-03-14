#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from typing import NamedTuple, Optional

from cmk.base.check_api import check_levels, get_percent_human_readable

poe_default_levels = (90.0, 95.0)


#  constants for operational status of poe interface
class PoeStatus(enum.IntEnum):
    ON = 1
    OFF = 2
    FAULTY = 3


# PoE data
class PoeValues(NamedTuple):
    poe_max: float
    poe_used: float
    poe_status: PoeStatus
    poe_status_detail: Optional[str]


def check_poe_data(params, poe_data):
    # data sanity-check
    if poe_data.poe_max < 0 or poe_data.poe_used < 0 or poe_data.poe_status not in range(1, 4):
        return (
            3,
            "Device returned faulty data: nominal power: %s, power consumption: %s, operational status: %s"
            % (
                str(poe_data.poe_max),
                str(poe_data.poe_used),
                str(poe_data.poe_status),
            ),
        )

    # PoE on device is turned ON
    if poe_data.poe_status == PoeStatus.ON:

        # calculate percentage of power consumption
        poe_used_percentage = (
            ((float(poe_data.poe_used) / float(poe_data.poe_max)) * 100)
            if poe_data.poe_max > 0
            else 0
        )

        return check_levels(
            poe_used_percentage,
            "power_usage_percentage",
            params.get("levels", poe_default_levels),
            human_readable_func=get_percent_human_readable,
            infoname="POE usage (%sW/%sW): " % (poe_data.poe_used, poe_data.poe_max),
        )

    # PoE on device is turned OFF
    if poe_data.poe_status == PoeStatus.OFF:
        return 0, "Operational status of the PSE is OFF"

    # PoE on device is FAULTY
    if poe_data.poe_status == PoeStatus.FAULTY:
        fault_detail = ""
        if poe_data.poe_status_detail:
            # optionally concat fault detail string
            fault_detail = " (%s)" % poe_data.poe_status_detail
        return 2, "Operational status of the PSE is FAULTY" + fault_detail
