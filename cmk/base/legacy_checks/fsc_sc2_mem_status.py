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


def parse_fsc_sc2_mem_status(string_table: StringTable) -> StringTable:
    return string_table


# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.1 "DIMM-1A"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.2 "DIMM-2A"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.3 "DIMM-3A"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.4 "DIMM-1B"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.5 "DIMM-2B"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.6 "DIMM-3B"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.7 "DIMM-1C"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.8 "DIMM-2C"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.3.1.9 "DIMM-3C"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.1 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.2 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.3 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.4 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.5 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.6 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.7 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.8 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.4.1.9 2
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.1 4096
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.2 -1
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.3 -1
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.4 4096
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.5 -1
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.6 -1
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.7 4096
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.8 -1
# .1.3.6.1.4.1.231.2.10.2.2.10.6.5.1.6.1.9 -1


def discover_fsc_sc2_mem_status(info):
    for line in info:
        if line[1] != "2":
            yield line[0], None


def check_fsc_sc2_mem_status(item, _no_params, info):
    def get_mem_status(status):
        return {
            "1": (3, "unknown"),
            "2": (3, "not-present"),
            "3": (0, "ok"),
            "4": (0, "disabled"),
            "5": (2, "error"),
            "6": (2, "failed"),
            "7": (1, "prefailure-predicted"),
            "11": (0, "hidden"),
        }.get(status, (3, "unknown"))

    for designation, status, capacity in info:
        if designation == item:
            status_state, status_txt = get_mem_status(status)
            return status_state, f"Status is {status_txt}, Size {capacity} MB"


check_info["fsc_sc2_mem_status"] = LegacyCheckDefinition(
    name="fsc_sc2_mem_status",
    parse_function=parse_fsc_sc2_mem_status,
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.6.5.1",
        oids=["3", "4", "6"],
    ),
    service_name="FSC %s",
    discovery_function=discover_fsc_sc2_mem_status,
    check_function=check_fsc_sc2_mem_status,
)
