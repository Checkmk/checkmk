#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file

from .mem import check_memory_element, get_levels_mode_from_value
from .size_trend import size_trend

CISCO_MEM_CHECK_DEFAULT_PARAMETERS = {
    "levels": (80.0, 90.0),
}


def scan_cisco_mem_asa64(oid):
    version = int((oid(".1.3.6.1.2.1.1.1.0").split("Version")[-1]).split(".")[0])
    return version >= 9


def inventory_cisco_mem(info):
    return [(line[0], {}) for line in info if line[0] != "Driver text"]


def check_cisco_mem(item, params, info):
    for line in info:

        if line[0] != item:
            continue

        if isinstance(params, tuple):
            params = {"levels": params}

        # We saw SNMP outputs which may contain empty entries for free or used memory.
        # Assumption: In this case these values are zero.
        try:
            mem_free = int(line[2])
        except ValueError:
            mem_free = 0
        try:
            mem_used = int(line[1])
        except ValueError:
            mem_used = 0
        mem_total = mem_free + mem_used
        return check_cisco_mem_sub(item, params, mem_used, mem_total)


def _convert_free_perc_levels(warn_perc_free_mem, crit_perc_free_mem):
    warn_perc_used = 100.0 - warn_perc_free_mem
    crit_perc_used = 100.0 - crit_perc_free_mem
    return warn_perc_used, crit_perc_used


def _convert_absolute_levels(warn_abs, crit_abs, mem_total):
    warn_perc = warn_abs / mem_total * 100.0
    crit_perc = crit_abs / mem_total * 100.0
    return warn_perc, crit_perc


def check_cisco_mem_sub(item, params, mem_used, mem_total):
    if not mem_total:
        return 3, "Cannot calculate memory usage: Device reports total memory 0"

    warn, crit = params.get("levels", (None, None))
    mode = get_levels_mode_from_value(warn)
    if isinstance(warn, int):
        warn *= 1048576  # convert from megabyte to byte
        crit *= 1048576
    if warn is not None:
        warn = abs(warn)
        crit = abs(crit)

    status, infotext, perfdata = check_memory_element(
        "Usage",
        mem_used,
        mem_total,
        (mode, (warn, crit)),
        create_percent_metric=True,
    )

    perfdata = [perfdata[-1]]  # Only the percent metric

    if params.get("trend_range"):
        mem_used_mb, mem_total_mb = mem_used / 1048576.0, mem_total / 1048576.0
        trend_status, trend_infotext, trend_perfdata = size_trend(
            "cisco_mem", item, "memory", params, mem_used_mb, mem_total_mb
        )
        status = max(status, trend_status)
        infotext += trend_infotext
        perfdata.extend(trend_perfdata)
    return status, infotext, perfdata
