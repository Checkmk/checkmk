#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.base.check_api import check_levels
from cmk.base.plugins.agent_based.utils.cpu import ProcessorType
from cmk.base.plugins.agent_based.utils.cpu_load import _processor_type_info

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file

# Common code for all CPU load checks. Please do not mix this up
# with CPU utilization. The load is at any time the current number
# of processes in the running state (on some systems, like Linux,
# also Disk wait is account for the load).


def _format_cores_info(
    num_cpus: int,
    processor_type: ProcessorType,
    load_per_core: float,
) -> str:
    return " at %d %s (%.2f per core)" % (
        num_cpus,
        f"{_processor_type_info(processor_type)}cores",
        load_per_core,
    )


# load is a triple of three floats: average load of
# the last 1, 5 or 15 minutes
def check_cpu_load_generic(params, load, num_cpus=1, processor_type=ProcessorType.unspecified):
    # Prepare performance data
    levels = params.get("levels")
    if isinstance(levels, tuple):
        # fixed levels
        warn, crit = [p * num_cpus for p in levels]
    else:
        # predictive levels
        warn, crit = None, None

    perfdata: Any = [
        ("load" + str(z), l, warn, crit, 0, num_cpus)
        for (z, l) in [(1, load[0]), (5, load[1]), (15, load[2])]
    ]

    state, infotext, perf = check_levels(
        load[2], "load15", levels, factor=num_cpus, infoname="15 min load"
    )
    perfdata += perf[1:]
    if num_cpus > 1:
        infotext += _format_cores_info(num_cpus, processor_type, load[2] / num_cpus)
    return state, infotext, perfdata
