#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<vms_queuejobs>>>
# 2036F23D SRV_WATCHPROD LEF 0 05:10:00.39 945007498 7721395
# 20201AF1 DRS_WATCHDOG_22 LEF 0 00:01:39.97 284611 2030


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)


def discover_vms_queuejobs(section: StringTable) -> DiscoveryResult:  # noqa: ARG001
    yield Service()


def check_vms_queuejobs(section: StringTable) -> CheckResult:
    names = []
    max_cpu_secs = 0.0
    max_cpu_job = None
    for _id, name, _state, cpu_days, cpu_time, _ios, _pgfaults in section:
        names.append(name)
        hours, minutes, seconds = map(float, cpu_time.split(":"))
        cpu_secs = int(cpu_days) * 86400 + hours * 3600 + minutes * 60 + seconds
        if cpu_secs > max_cpu_secs:
            max_cpu_secs = cpu_secs
            max_cpu_job = name

    infotext = f"{len(section)} jobs"
    if max_cpu_job:
        minutes, seconds = divmod(max_cpu_secs, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        infotext += (
            f", most CPU used by {max_cpu_job}"
            f" ({int(days)} days, {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}.{int(seconds * 100):02d})"
        )

    yield Result(state=State.OK, summary=infotext)


def parse_vms_queuejobs(string_table: StringTable) -> StringTable:
    return string_table


agent_section_vms_queuejobs = AgentSection(
    name="vms_queuejobs",
    parse_function=parse_vms_queuejobs,
)

check_plugin_vms_queuejobs = CheckPlugin(
    name="vms_queuejobs",
    service_name="Queue Jobs",
    discovery_function=discover_vms_queuejobs,
    check_function=check_vms_queuejobs,
)
