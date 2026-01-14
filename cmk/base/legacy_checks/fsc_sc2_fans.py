#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.base.check_legacy_includes.fsc import DETECT_FSC_SC2

check_info = {}


def parse_fsc_sc2_fans(string_table: StringTable) -> StringTable:
    return string_table


# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.1 "FAN1 SYS"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.2 "FAN2 SYS"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.3 "FAN3 SYS"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.4 "FAN4 SYS"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.5 "FAN5 SYS"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.6 "FAN PSU1"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.1.7 "FAN PSU2"
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.1 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.2 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.3 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.4 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.5 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.6 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.5.1.7 3
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.1 5820
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.2 6000
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.3 6000
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.4 6000
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.5 6120
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.6 2400
# .1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.6.1.7 2400


def discover_fsc_sc2_fans(info):
    for line in info:
        if line[1] not in ["8"]:
            yield line[0], {}


def check_fsc_sc2_fans(item, params, info):
    status_map = {
        "1": (3, "Status is unknown"),
        "2": (0, "Status is disabled"),
        "3": (0, "Status is ok"),
        "4": (2, "Status is failed"),
        "5": (1, "Status is prefailure-predicted"),
        "6": (1, "Status is redundant-fan-failed"),
        "7": (3, "Status is not-manageable"),
        "8": (0, "Status is not-present"),
    }

    if isinstance(params, tuple):
        params = {"lower": params}

    for designation, status, rpm in info:
        if designation == item:
            yield status_map.get(status, (3, "Status is unknown"))
            if rpm:
                yield check_fan(int(rpm), params)
            else:
                yield 0, "Device did not deliver RPM values"


check_info["fsc_sc2_fans"] = LegacyCheckDefinition(
    name="fsc_sc2_fans",
    parse_function=parse_fsc_sc2_fans,
    detect=DETECT_FSC_SC2,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.10.5.2.1",
        oids=["3", "5", "6"],
    ),
    service_name="FSC %s",
    discovery_function=discover_fsc_sc2_fans,
    check_function=check_fsc_sc2_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (1500, 2000),
    },
)
