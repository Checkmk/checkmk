#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.fsc import DETECT_FSC_SC2

check_info = {}


def parse_fsc_sc2_cpu_status(string_table: StringTable) -> StringTable:
    return string_table


# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.3.1.1 "CPU1"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.3.1.2 "CPU2"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.4.1.1 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.4.1.2 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.5.1.1 "Intel(R) Xeon(R) CPU E5-2620 v2 @ 2.10GHz"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.5.1.2 ""
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.8.1.1 2100
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.8.1.2 0
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.13.1.1 6
# .1.3.6.1.4.1.231.2.10.2.2.10.6.4.1.13.1.2 0


def discover_fsc_sc2_cpu_status(info):
    for line in info:
        if line[1] != "2":
            yield line[0], None


def check_fsc_sc2_cpu_status(item, _no_params, info):
    def get_cpu_status(status):
        return {
            "1": (3, "unknown"),
            "2": (3, "not-present"),
            "3": (0, "ok"),
            "4": (0, "disabled"),
            "5": (2, "error"),
            "6": (2, "failed"),
            "7": (1, "missing-termination"),
            "8": (1, "prefailure-warning"),
        }.get(status, (3, "unknown"))

    for designation, status, model, speed, cores in info:
        if designation == item:
            status_state, status_txt = get_cpu_status(status)
            return status_state, f"Status is {status_txt}, {model}, {cores} cores @ {speed} MHz"


check_info["fsc_sc2_cpu_status"] = LegacyCheckDefinition(
    name="fsc_sc2_cpu_status",
    parse_function=parse_fsc_sc2_cpu_status,
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.6.4.1",
        oids=["3", "4", "5", "8", "13"],
    ),
    service_name="FSC %s",
    discovery_function=discover_fsc_sc2_cpu_status,
    check_function=check_fsc_sc2_cpu_status,
)
