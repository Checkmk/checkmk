#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

check_info = {}

# Example output from agent:
# <<<vms_cpu>>>
# 1 99.17 0.54 0.18 0.00


def parse_vms_cpu(string_table):
    parsed: dict[str, int | float] = {}
    try:
        parsed["num_cpus"] = int(string_table[0][0])
        for i, key in enumerate(("idle", "user", "wait_interrupt", "wait_npsync"), 1):
            parsed[key] = float(string_table[0][i]) / parsed["num_cpus"]
    except (IndexError, ValueError):
        return {}

    return parsed


def discover_vms_cpu(info):
    if info:
        yield None, {}


def check_vms_cpu(_no_item, params, parsed):
    user = parsed["user"]
    wait = parsed["wait_interrupt"] + parsed["wait_npsync"]
    util = 100.0 - parsed["idle"]
    system = util - user - wait

    yield check_levels(user, "user", None, human_readable_func=render.percent, infoname="User")
    yield check_levels(
        system, "system", None, human_readable_func=render.percent, infoname="System"
    )
    yield check_levels(
        wait,
        "wait",
        params.get("iowait"),
        human_readable_func=render.percent,
        infoname="Wait",
    )

    yield from check_cpu_util(util, params)

    num_cpus = parsed["num_cpus"]
    unit = "CPU" if num_cpus == 1 else "CPUs"
    yield check_levels(
        num_cpus,
        "cpu_entitlement",
        None,
        human_readable_func=lambda x, u=unit: f"{int(x)} {u}",
        infoname="100% corresponding to",
    )


check_info["vms_cpu"] = LegacyCheckDefinition(
    name="vms_cpu",
    parse_function=parse_vms_cpu,
    service_name="CPU utilization",
    discovery_function=discover_vms_cpu,
    check_function=check_vms_cpu,
    check_ruleset_name="cpu_iowait",
)
