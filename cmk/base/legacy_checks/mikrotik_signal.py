#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree, StringTable

check_info = {}


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def discover_mikrotik_signal(info):
    yield from ((network, {}) for network, _strength, _mode in info)


def check_mikrotik_signal(item, params, info):
    warn, crit = params["levels_lower"]
    for network, strength, mode in info:
        if network == item:
            strength = saveint(strength)
            quality = 0
            if strength <= -50 or strength >= -100:
                quality = 2 * (strength + 100)
            quality = min(quality, 100)

            infotext = "Signal quality %d%% (%ddBm). Mode is: %s" % (quality, strength, mode)
            perf = [("quality", quality, warn, crit)]
            if quality <= crit:
                return 2, infotext, perf
            if quality <= warn:
                return 1, infotext, perf
            return 0, infotext, perf

    return 3, "Network not found"


def parse_mikrotik_signal(string_table: StringTable) -> StringTable:
    return string_table


check_info["mikrotik_signal"] = LegacyCheckDefinition(
    name="mikrotik_signal",
    parse_function=parse_mikrotik_signal,
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14988.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14988.1.1.1.1.1",
        oids=["5.2", "4.2", "8.2"],
    ),
    service_name="Signal %s",
    discovery_function=discover_mikrotik_signal,
    check_function=check_mikrotik_signal,
    check_ruleset_name="signal_quality",
    check_default_parameters={
        "levels_lower": (80.0, 70.0),
    },
)
