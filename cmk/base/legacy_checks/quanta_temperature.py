#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.quanta import parse_quanta
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.lib.quanta import DETECT_QUANTA

check_info = {}

# .1.3.6.1.4.1.7244.1.2.1.3.4.1.1.1 1
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.1.2 2
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.2.1 3
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.2.2 2
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.3.1 "54 65 6D 70 5F 50 43 49 31 5F 4F 75 74 6C 65 74 01 "
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.3.2 Temp_CPU0_Inlet
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.4.1 41
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.4.2 37
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.6.1 85
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.6.2 75
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.7.1 80
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.7.2 70
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.8.1 -99
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.8.2 -99
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.9.25 -99
# .1.3.6.1.4.1.7244.1.2.1.3.4.1.9.26 5


def check_quanta_temperature(item, params, parsed):
    if not (entry := parsed.get(item)):
        return

    if entry.value in (-99, None):
        yield entry.status[0], "Status: %s" % entry.status[1]
        return

    yield check_temperature(
        entry.value,
        params,
        "quanta_temperature_%s" % entry.name,
        dev_levels=entry.upper_levels,
        dev_levels_lower=entry.lower_levels,
        dev_status=entry.status[0],
        dev_status_name=entry.status[1],
    )


def discover_quanta_temperature(section):
    yield from ((item, {}) for item in section)


check_info["quanta_temperature"] = LegacyCheckDefinition(
    name="quanta_temperature",
    detect=DETECT_QUANTA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.7244.1.2.1.3.4.1",
            oids=["1", "2", "3", "4", "6", "7", "8", "9"],
        )
    ],
    parse_function=parse_quanta,
    service_name="Temperature %s",
    discovery_function=discover_quanta_temperature,
    check_function=check_quanta_temperature,
    check_ruleset_name="temperature",
)
