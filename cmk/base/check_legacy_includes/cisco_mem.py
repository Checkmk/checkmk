#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from .mem import check_memory_element, get_levels_mode_from_value
from .size_trend import size_trend


# TODO: Remove this function/entire file when migrating cisco_cpu_memory.
# Move cmk/base/plugins/agent_based/cisco_mem.py:_check_cisco_mem_sub to utils
# and use it instead, then.
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
