#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from collections.abc import Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.plugins.lib.stulz import DETECT_STULZ

check_info = {}

Section = Mapping[str, str]


def parse_stulz_alerts(string_table: StringTable) -> Section:
    parsed: dict[str, str] = {}
    for oidend, value in string_table:
        bus, unit = oidend.split(".")[0:2]
        parsed.setdefault(f"{bus}-{unit}", value)
    return parsed


def inventory_stulz_alerts(section):
    return [(item, None) for item in section]


def check_stulz_alerts(item, _no_params, section):
    if item in section:
        if section[item] != "0":
            return 2, "Device is in alert state"
        return 0, "No alerts on device"
    return None


check_info["stulz_alerts"] = LegacyCheckDefinition(
    name="stulz_alerts",
    parse_function=parse_stulz_alerts,
    detect=DETECT_STULZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.29462.10.2.1.4.4.1.1.1",
        oids=[OIDEnd(), "1010"],
    ),
    service_name="Alerts %s ",
    discovery_function=inventory_stulz_alerts,
    check_function=check_stulz_alerts,
)
