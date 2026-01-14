#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.fsc import DETECT_FSC_SC2

check_info = {}

# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.3.1.1 "PSU1"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.3.1.2 "PSU2"
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.5.1.1 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.5.1.2 3
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.6.1.1 52
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.6.1.2 40
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.7.1.1 448
# .1.3.6.1.4.1.231.2.10.2.2.10.6.2.1.7.1.2 448


def discover_fsc_sc2_psu(info):
    for line in info:
        if line[1] not in ["2"]:
            yield line[0], None


def check_fsc_sc2_psu(item, _no_params, info):
    psu_status = {
        "1": (3, "Status is unknown"),
        "2": (1, "Status is not-present"),
        "3": (0, "Status is ok"),
        "4": (2, "Status is failed"),
        "5": (2, "Status is ac-fail"),
        "6": (2, "Status is dc-fail"),
        "7": (2, "Status is critical-temperature"),
        "8": (1, "Status is not-manageable"),
        "9": (1, "Status is fan-failure-predicted"),
        "10": (2, "Status is fan-failure"),
        "11": (1, "Status is power-safe-mode"),
        "12": (1, "Status is non-redundant-dc-fail"),
        "13": (1, "Status is non-redundant-ac-fail"),
    }

    for designation, status, load, nominal in info:
        if designation == item:
            yield psu_status.get(status, (3, "Status is unknown"))
            if nominal and load:
                infotext = f"Nominal load: {nominal} W, Actual load: {load} W"
                perfdata = [("power", int(load))]
            else:
                infotext = "Did not receive load data"
                perfdata = []
            yield 0, infotext, perfdata


def parse_fsc_sc2_psu(string_table: StringTable) -> StringTable:
    return string_table


check_info["fsc_sc2_psu"] = LegacyCheckDefinition(
    name="fsc_sc2_psu",
    parse_function=parse_fsc_sc2_psu,
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.6.2.1",
        oids=["3", "5", "6", "7"],
    ),
    service_name="FSC %s",
    discovery_function=discover_fsc_sc2_psu,
    check_function=check_fsc_sc2_psu,
)
