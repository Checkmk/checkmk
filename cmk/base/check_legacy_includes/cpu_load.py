#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.check_api import check_levels
# Common code for all CPU load checks. Please do not mix this up
# with CPU utilization. The load is at any time the current number
# of processes in the running state (on some systems, like Linux,
# also Disk wait is account for the load).

from enum import Enum


class ProcessorType(Enum):
    unspecified = 0
    physical = 1
    logical = 2


def _format_cores_info(num_cpus, processor_type, load_per_core):
    if processor_type == ProcessorType.unspecified:
        cores_info = "cores"
    else:
        cores_info = "%s cores" % processor_type.name
    return " at %d %s (%.2f per core)" % (num_cpus, cores_info, load_per_core)


# load is a triple of three floats: average load of
# the last 1, 5 or 15 minutes
def check_cpu_load_generic(params, load, num_cpus=1, processor_type=ProcessorType.unspecified):
    # Prepare performance data
    if isinstance(params, tuple):
        warn, crit = [p * num_cpus for p in params]
    else:
        warn, crit = None, None

    perfdata = [('load' + str(z), l, warn, crit, 0, num_cpus)
                for (z, l) in [(1, load[0]), (5, load[1]), (15, load[2])]]

    state, infotext, perf = check_levels(load[2],
                                         'load15',
                                         params,
                                         factor=num_cpus,
                                         infoname="15 min load")
    perfdata += perf[1:]
    if num_cpus > 1:
        infotext += _format_cores_info(num_cpus, processor_type, load[2] / num_cpus)
    return state, infotext, perfdata
