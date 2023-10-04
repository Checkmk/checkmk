#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, SNMPTree

mikrotik_signal_default_levels = (80, 70)


def inventory_mikrotik_signal(info):
    inventory = []
    for network, _strength, _mode in info:
        inventory.append((network, mikrotik_signal_default_levels))
    return inventory


def check_mikrotik_signal(item, params, info):
    warn, crit = params
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


check_info["mikrotik_signal"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14988.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14988.1.1.1.1.1",
        oids=["5.2", "4.2", "8.2"],
    ),
    service_name="Signal %s",
    discovery_function=inventory_mikrotik_signal,
    check_function=check_mikrotik_signal,
    check_ruleset_name="signal_quality",
)
