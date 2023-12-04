#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import check_levels

# .
#   .--Disk Usage----------------------------------------------------------.
#   |            ____  _     _      _   _                                  |
#   |           |  _ \(_)___| | __ | | | |___  __ _  __ _  ___             |
#   |           | | | | / __| |/ / | | | / __|/ _` |/ _` |/ _ \            |
#   |           | |_| | \__ \   <  | |_| \__ \ (_| | (_| |  __/            |
#   |           |____/|_|___/_|\_\  \___/|___/\__,_|\__, |\___|            |
#   |                                               |___/                  |
#   '----------------------------------------------------------------------'


def inventory_arbor_disk_usage(parsed):
    if "disk" in parsed:
        return [("/", {})]
    return []


def check_arbor_disk_usage(_no_item, params, parsed):
    usage = int(parsed["disk"])
    yield check_levels(usage, None, params["levels"], infoname="Disk usage")
    yield 0, "", [("disk_utilization", float(usage) / 100.0)]


# .
#   .--Host Fault----------------------------------------------------------.
#   |             _   _           _     _____           _ _                |
#   |            | | | | ___  ___| |_  |  ___|_ _ _   _| | |_              |
#   |            | |_| |/ _ \/ __| __| | |_ / _` | | | | | __|             |
#   |            |  _  | (_) \__ \ |_  |  _| (_| | |_| | | |_              |
#   |            |_| |_|\___/|___/\__| |_|  \__,_|\__,_|_|\__|             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_arbor_host_fault(parsed):
    if "host_fault" in parsed:
        return [(None, None)]
    return []


def check_arbor_host_fault(_no_item, _no_params, parsed):
    status = 0
    if parsed["host_fault"] != "No Fault":
        status = 2
    return status, parsed["host_fault"]


# .
#   .--Drop Rate-----------------------------------------------------------.
#   |             ____                    ____       _                     |
#   |            |  _ \ _ __ ___  _ __   |  _ \ __ _| |_ ___               |
#   |            | | | | '__/ _ \| '_ \  | |_) / _` | __/ _ \              |
#   |            | |_| | | | (_) | |_) | |  _ < (_| | ||  __/              |
#   |            |____/|_|  \___/| .__/  |_| \_\__,_|\__\___|              |
#   |                            |_|                                       |
#   '----------------------------------------------------------------------'


def inventory_arbor_drop_rate(parsed):
    if "drop_rate" in parsed:
        return [("Overrun", {})]
    return []


def check_arbor_drop_rate(_no_item, params, parsed):
    drop_rate = int(parsed["drop_rate"])
    lower_levels = params.get("levels_lower") or (None, None)
    upper_levels = params.get("levels") or (None, None)
    yield check_levels(
        drop_rate,
        "if_in_pkts",
        upper_levels + lower_levels,
        human_readable_func=lambda x: "%.1f pps",
    )


# .
