#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="assignment"

from cmk.base.check_api import check_levels, get_percent_human_readable, LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.check_legacy_includes.transforms import transform_cpu_iowait
from cmk.base.config import check_info

# Example output from agent:
# <<<vms_cpu>>>
# 1 99.17 0.54 0.18 0.00


def parse_vms_cpu(info):
    parsed = {}
    try:
        parsed["num_cpus"] = int(info[0][0])
        for i, key in enumerate(("idle", "user", "wait_interrupt", "wait_npsync"), 1):
            parsed[key] = float(info[0][i]) / parsed["num_cpus"]
    except (IndexError, ValueError):
        return {}

    return parsed


def inventory_vms_cpu(info):
    if info:
        yield None, {}


def check_vms_cpu(_no_item, params, parsed):
    # ancient tuple rule
    # and legacy default None prior to 1.6
    params = transform_cpu_iowait(params)

    user = parsed["user"]
    wait = parsed["wait_interrupt"] + parsed["wait_npsync"]
    util = 100.0 - parsed["idle"]
    system = util - user - wait

    yield check_levels(
        user, "user", None, human_readable_func=get_percent_human_readable, infoname="User"
    )
    yield check_levels(
        system, "system", None, human_readable_func=get_percent_human_readable, infoname="System"
    )
    yield check_levels(
        wait,
        "wait",
        params.get("iowait"),
        human_readable_func=get_percent_human_readable,
        infoname="Wait",
    )

    for util_result in check_cpu_util(util, params):
        yield util_result

    num_cpus = parsed["num_cpus"]
    unit = "CPU" if num_cpus == 1 else "CPUs"
    yield check_levels(
        num_cpus, "cpu_entitlement", None, unit=unit, infoname="100% corresponding to"
    )


check_info["vms_cpu"] = LegacyCheckDefinition(
    parse_function=parse_vms_cpu,
    check_function=check_vms_cpu,
    discovery_function=inventory_vms_cpu,
    service_name="CPU utilization",
    check_ruleset_name="cpu_iowait",
)
