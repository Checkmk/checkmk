#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent
# Columns:
# 1. Direct IOs / sec   (on hardware)
# 2. Buffered IOs / sec (queued)
# 3. Number of currently existing processes (averaged)

# <<<vms_system>>>
# 0.00 0.00 15.00


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info


def inventory_vms_system(info):
    if len(info) > 0:
        return [(None, None)]
    return []


def check_vms_system_ios(_no_item, _no_params, info):
    direct_ios, buffered_ios = map(float, info[0][:2])
    return (
        0,
        f"Direct IOs: {direct_ios:.2f}/sec, Buffered IOs: {buffered_ios:.2f}/sec",
        [("direct", direct_ios), ("buffered", buffered_ios)],
    )


check_info["vms_system.ios"] = LegacyCheckDefinition(
    service_name="IOs",
    sections=["vms_system"],
    discovery_function=inventory_vms_system,
    check_function=check_vms_system_ios,
)


def check_vms_system_procs(_no_item, params, info):
    procs = int(float(info[0][2]))
    perfdata = [("procs", procs, None, None, 0)]

    if params:
        warn, crit = params
        perfdata = [("procs", procs, warn, crit, 0)]
        if procs >= crit:
            return (2, "%d processes (critical at %d)" % (procs, crit), perfdata)
        if procs >= warn:
            return (1, "%d processes (warning at %d)" % (procs, warn), perfdata)

    return (0, "%d processes" % (procs,), perfdata)


check_info["vms_system.procs"] = LegacyCheckDefinition(
    service_name="Number of processes",
    sections=["vms_system"],
    discovery_function=inventory_vms_system,
    check_function=check_vms_system_procs,
    check_ruleset_name="vms_procs",
)
