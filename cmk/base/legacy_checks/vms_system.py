#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Example output from agent
# Columns:
# 1. Direct IOs / sec   (on hardware)
# 2. Buffered IOs / sec (queued)
# 3. Number of currently existing processes (averaged)

# <<<vms_system>>>
# 0.00 0.00 15.00


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def parse_vms_system(string_table: StringTable) -> StringTable:
    return string_table


check_info["vms_system"] = LegacyCheckDefinition(
    name="vms_system",
    parse_function=parse_vms_system,
)


def discover_vms_system(info):
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
    name="vms_system_ios",
    service_name="IOs",
    sections=["vms_system"],
    discovery_function=discover_vms_system,
    check_function=check_vms_system_ios,
)


def check_vms_system_procs(_no_item, params, info):
    procs = int(float(info[0][2]))

    yield check_levels(
        procs,
        "procs",
        params["levels_upper"],
        human_readable_func=str,
        infoname="Processes",
        boundaries=(0, None),
    )


check_info["vms_system.procs"] = LegacyCheckDefinition(
    name="vms_system_procs",
    service_name="Number of processes",
    sections=["vms_system"],
    discovery_function=discover_vms_system,
    check_function=check_vms_system_procs,
    check_ruleset_name="vms_procs",
    check_default_parameters={"levels_upper": None},
)
