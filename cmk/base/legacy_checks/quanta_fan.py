#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.base.check_legacy_includes.quanta import parse_quanta
from cmk.plugins.lib.quanta import DETECT_QUANTA

check_info = {}

# .1.3.6.1.4.1.7244.1.2.1.3.3.1.1.1 1
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.1.2 2
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.2.1 3
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.2.2 3
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.3.1 Fan_SYS0_1
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.3.2 Fan_SYS0_2
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.4.1 100
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.4.2 9400
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.6.1 -99
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.6.2 -99
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.7.1 -99
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.7.2 -99
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.8.1 -99
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.8.2 -99
# ...
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.9.1 500
# .1.3.6.1.4.1.7244.1.2.1.3.3.1.9.2 500


def check_quanta_fan(item, params, parsed):
    if not (entry := parsed.get(item)):
        return

    yield entry.status[0], "Status: %s" % entry.status[1]

    if entry.value in (-99, None):
        return

    levels = {
        "upper": params.get("upper", entry.upper_levels),
        "lower": params.get("lower", entry.lower_levels),
    }

    yield check_fan(entry.value, levels)


def discover_quanta_fan(section):
    yield from ((item, {}) for item in section)


check_info["quanta_fan"] = LegacyCheckDefinition(
    name="quanta_fan",
    detect=DETECT_QUANTA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.7244.1.2.1.3.3.1",
            oids=["1", "2", "3", "4", "6", "7", "8", "9"],
        )
    ],
    parse_function=parse_quanta,
    service_name="Fan %s",
    discovery_function=discover_quanta_fan,
    check_function=check_quanta_fan,
    check_ruleset_name="hw_fans",
)
