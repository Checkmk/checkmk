#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.plugins.bvip.lib import DETECT_BVIP

check_info = {}


def discover_bvip_fans(info):
    for line in info:
        rpm = int(line[1])
        if rpm != 0:
            yield line[0], {"lower": (rpm * 0.9, rpm * 0.8)}


def check_bvip_fans(item, params, info):
    for nr, value in info:
        if nr == item:
            rpm = int(value)
            return check_fan(rpm, params)
    return None


def parse_bvip_fans(string_table: StringTable) -> StringTable:
    return string_table


check_info["bvip_fans"] = LegacyCheckDefinition(
    name="bvip_fans",
    parse_function=parse_bvip_fans,
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1.1.8.1",
        oids=[OIDEnd(), "1"],
    ),
    service_name="Fan %s",
    discovery_function=discover_bvip_fans,
    check_function=check_bvip_fans,
    check_ruleset_name="hw_fans",
)
