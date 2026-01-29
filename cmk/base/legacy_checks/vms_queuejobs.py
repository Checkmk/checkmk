#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<vms_queuejobs>>>
# 2036F23D SRV_WATCHPROD LEF 0 05:10:00.39 945007498 7721395
# 20201AF1 DRS_WATCHDOG_22 LEF 0 00:01:39.97 284611 2030


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_vms_queuejobs(info: StringTable) -> list[tuple[None, dict[str, object]]]:
    return [(None, {})]


def check_vms_queuejobs(
    _no_item: None, params: Mapping[str, Any], info: StringTable
) -> tuple[int, str]:
    names = []
    max_cpu_secs = 0.0
    max_cpu_job = None
    for _id, name, _state, cpu_days, cpu_time, _ios, _pgfaults in info:
        names.append(name)
        hours, minutes, seconds = map(float, cpu_time.split(":"))
        cpu_secs = int(cpu_days) * 86400 + hours * 3600 + minutes * 60 + seconds
        if cpu_secs > max_cpu_secs:
            max_cpu_secs = cpu_secs
            max_cpu_job = name

    infotext = "%d jobs" % len(info)
    if max_cpu_job:
        minutes, seconds = divmod(max_cpu_secs, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        infotext += ", most CPU used by %s (%d days, %02d:%02d:%02d.%02d)" % (
            max_cpu_job,
            days,
            hours,
            minutes,
            int(seconds),
            int(seconds * 100),
        )

    return 0, infotext


def parse_vms_queuejobs(string_table: StringTable) -> StringTable:
    return string_table


check_info["vms_queuejobs"] = LegacyCheckDefinition(
    name="vms_queuejobs",
    parse_function=parse_vms_queuejobs,
    service_name="Queue Jobs",
    discovery_function=discover_vms_queuejobs,
    check_function=check_vms_queuejobs,
)
