#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.acme import ACME_ENVIRONMENT_STATES
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.acme import DETECT_ACME

# .1.3.6.1.4.1.9148.3.3.1.4.1.1.3.1 MAIN FAN1 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusDescr.1
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.3.2 MAIN FAN2 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusDescr.2
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.3.3 MAIN FAN3 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusDescr.3
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.3.4 MAIN FAN4 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusDescr.4
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.4.1 100 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusValue.1
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.4.2 100 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusValue.2
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.4.3 100 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusValue.3
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.4.4 100 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanStatusValue.4
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.5.1 1 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanState.1
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.5.2 1 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanState.2
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.5.3 1 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanState.3
# .1.3.6.1.4.1.9148.3.3.1.4.1.1.5.4 1 --> ACMEPACKET-ENVMON-MIB::apEnvMonFanState.4


def inventory_acme_fan(info):
    return [(descr, {}) for descr, _value_str, state in info if state != "7"]


def check_acme_fan(item, params, info):
    for descr, value_str, state in info:
        if item == descr:
            dev_state, dev_state_readable = ACME_ENVIRONMENT_STATES[state]
            return dev_state, f"Status: {dev_state_readable}, Speed: {value_str}%"
    return None


def parse_acme_fan(string_table: StringTable) -> StringTable:
    return string_table


check_info["acme_fan"] = LegacyCheckDefinition(
    parse_function=parse_acme_fan,
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.3.1.4.1.1",
        oids=["3", "4", "5"],
    ),
    service_name="Fan %s",
    discovery_function=inventory_acme_fan,
    check_function=check_acme_fan,
    check_ruleset_name="hw_fans_perc",
)
