#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import get_bytes_human_readable, get_percent_human_readable


# DEPRECATED: Please use check_memory_element from mem.inlude!
def check_memory_simple(used, total, params):
    # Convert old-style tuple params to dict
    if params:
        if isinstance(params, tuple):
            params = {"levels": ("perc_used", params)}
    else:
        params = {"levels": ("ignore")}

    perc_used = (float(used) / total) * 100
    infotext = "Usage: %s (Used: %s, Total: %s)" % (
        get_percent_human_readable(perc_used),
        get_bytes_human_readable(used),
        get_bytes_human_readable(total),
    )

    status = 0
    if params["levels"][0] == "perc_used":
        warn_perc, crit_perc = params["levels"][1]
        warn_abs = (warn_perc / 100.0) * total
        crit_abs = (crit_perc / 100.0) * total
        levelstext = " (warn/crit at %s/%s used)" % (
            get_percent_human_readable(warn_perc),
            get_percent_human_readable(crit_perc),
        )

    elif params["levels"][0] == "abs_free":
        warn_abs_free, crit_abs_free = params["levels"][1]
        warn_abs = total - warn_abs_free
        crit_abs = total - crit_abs_free
        levelstext = " (warn/crit below %s/%s free)" % (
            get_bytes_human_readable(warn_abs_free),
            get_bytes_human_readable(crit_abs_free),
        )

    else:
        # No levels imposed, ie. params = {'levels': 'ignore'}
        crit_abs = None
        warn_abs = None
        levelstext = ""

    if crit_abs is not None and used >= crit_abs:
        status = 2
    elif warn_abs is not None and used >= warn_abs:
        status = 1
    if status:
        infotext += levelstext

    perfdata = [("memory_used", used, warn_abs, crit_abs, 0, total)]
    return status, infotext, perfdata


# DEPRECATED: Please use check_memory_element from mem.inlude!
def check_memory_multiitem(params, data, base=1024):
    if "mem_total" not in data:
        return 3, "Invalid data: missing mem_total"
    mem_total = data["mem_total"]

    if "mem_used" in data:
        mem_used = data["mem_used"]
        mem_avail = mem_total - mem_used
    elif "mem_avail" in data:
        mem_avail = data["mem_avail"]
        mem_used = mem_total - mem_avail
    else:
        return 3, "Invalid data: missing mem_used or mem_avail sizes"

    infotext = "%s used (%s of %s)" % (
        get_percent_human_readable(float(mem_used) / float(mem_total) * 100),
        get_bytes_human_readable(mem_used, base=base),
        get_bytes_human_readable(mem_total, base=base),
    )

    state = 0
    if "levels" in params:
        warn, crit = params["levels"]
        if isinstance(warn, int):
            warn_absolute = warn
        else:
            warn_absolute = int(mem_total * warn / 100)

        if isinstance(crit, int):
            crit_absolute = crit
        else:
            crit_absolute = int(mem_total * crit / 100)

        if mem_used > crit_absolute:
            state = 2
        elif mem_used > warn_absolute:
            state = 1
        if state:
            infotext += " (warn/crit at %s/%s)" % (
                get_bytes_human_readable(warn_absolute),
                get_bytes_human_readable(crit_absolute),
            )
    else:
        warn_absolute = None
        crit_absolute = None

    return state, infotext, [("memused", mem_used, warn_absolute, crit_absolute, 0, mem_total)]
