#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.stulz.lib import DETECT_STULZ

check_info = {}


def discover_stulz_alerts(info):
    return [(x[0], None) for x in info]


def check_stulz_alerts(item, _no_params, info):
    for line in info:
        if line[0] == item:
            if line[1] != "0":
                return 2, "Device is in alert state"
            return 0, "No alerts on device"
    return 3, "No information found about the device"


def parse_stulz_alerts(string_table: StringTable) -> StringTable:
    return string_table


check_info["stulz_alerts"] = LegacyCheckDefinition(
    name="stulz_alerts",
    parse_function=parse_stulz_alerts,
    detect=DETECT_STULZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.4.4.1.1.1.1010",
        oids=[OIDEnd(), "1"],
    ),
    service_name="Alerts %s ",
    discovery_function=discover_stulz_alerts,
    check_function=check_stulz_alerts,
)
