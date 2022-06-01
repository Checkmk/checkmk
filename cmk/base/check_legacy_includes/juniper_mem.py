#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=no-else-return

from cmk.base.check_api import get_bytes_human_readable

juniper_mem_default_levels = (80.0, 90.0)


def inventory_juniper_mem_generic(info):
    return [(None, "juniper_mem_default_levels")]


def check_juniper_mem_generic(_no_item, params, info):
    usage_kb, mem_size_kb = map(int, info[0])  # Kilobyte
    mem_size = mem_size_kb * 1024
    usage = usage_kb * 1024
    usage_perc = (float(usage_kb) / mem_size_kb) * 100

    warn, crit = params
    warn_kb = (mem_size_kb / 100.0) * warn
    crit_kb = (mem_size_kb / 100.0) * crit
    perf = [("mem_used", usage, warn_kb * 1024, crit_kb * 1024, 0, mem_size)]
    message = "Used: %s/%s (%.0f%%)" % (
        get_bytes_human_readable(usage),
        get_bytes_human_readable(mem_size),
        usage_perc,
    )
    levels = " (warn/crit at %.0f%%/%0.f%%)" % (warn, crit)
    if usage_perc >= crit:
        return 2, message + levels, perf
    elif usage_perc >= warn:
        return 1, message + levels, perf
    return 0, message, perf
