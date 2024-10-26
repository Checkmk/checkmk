#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.quanta import parse_quanta

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.quanta import DETECT_QUANTA

check_info = {}

# .1.3.6.1.4.1.7244.1.2.1.3.5.1.1.14 14
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.1.15 15
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.2.14 3
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.2.15 3
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.3.14 Volt_VR_DIMM_GH
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.3.15 "56 6F 6C 74 5F 53 41 53 5F 45 58 50 5F 30 56 39 01 "
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.4.14 1220
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.4.15 923
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.6.14 1319
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.6.15 988
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.7.14 -99
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.7.15 -99
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.8.14 -99
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.8.15 -99
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.9.14 1079
# .1.3.6.1.4.1.7244.1.2.1.3.5.1.9.15 806


def check_quanta_voltage(item, params, parsed):
    if not (entry := parsed.get(item)):
        return
    yield entry.status[0], "Status: %s" % entry.status[1]

    if entry.value in (-99, None):
        return

    yield check_levels(
        entry.value,
        "voltage",
        params.get("levels", entry.upper_levels) + params.get("levels_lower", entry.lower_levels),
        unit="V",
    )


def discover_quanta_voltage(section):
    yield from ((item, {}) for item in section)


check_info["quanta_voltage"] = LegacyCheckDefinition(
    name="quanta_voltage",
    detect=DETECT_QUANTA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.7244.1.2.1.3.5.1",
            oids=["1", "2", "3", "4", "6", "7", "8", "9"],
        )
    ],
    parse_function=parse_quanta,
    service_name="Voltage %s",
    discovery_function=discover_quanta_voltage,
    check_function=check_quanta_voltage,
    check_ruleset_name="voltage",
)
