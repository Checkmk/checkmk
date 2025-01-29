#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.temperature import check_temperature

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.acme.agent_based.lib import ACME_ENVIRONMENT_STATES, DETECT_ACME

check_info = {}

# .1.3.6.1.4.1.9148.3.3.1.3.1.1.2.1 0 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusType.1
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.2.2 0 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusType.2
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.2.3 0 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusType.3
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.2.4 0 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusType.4
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.2.5 0 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusType.5
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.2.6 0 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusType.6
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.3.1 CPU TEMP0 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusDescr.1
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.3.2 MAIN TEMP0 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusDescr.2
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.3.3 MAIN TEMP1 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusDescr.3
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.3.4 PHY TEMP0 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusDescr.4
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.3.5 PHY TCM5 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusDescr.5
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.3.6 PHY FPGA TEMP0 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusDescr.6
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.4.1 57 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusValue.1
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.4.2 33 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusValue.2
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.4.3 30 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusValue.3
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.4.4 53 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusValue.4
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.4.5 44 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusValue.5
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.4.6 53 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureStatusValue.6
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.5.1 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureState.1
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.5.2 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureState.2
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.5.3 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureState.3
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.5.4 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureState.4
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.5.5 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureState.5
# .1.3.6.1.4.1.9148.3.3.1.3.1.1.5.6 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonTemperatureState.6


def inventory_acme_temp(info):
    return [(descr, {}) for descr, _value_str, state in info if state != "7"]


def check_acme_temp(item, params, info):
    for descr, value_str, state in info:
        if item == descr:
            dev_state, dev_state_readable = ACME_ENVIRONMENT_STATES[state]
            return check_temperature(
                float(value_str),
                params,
                "acme_temp.%s" % item,
                dev_status=int(dev_state),
                dev_status_name=dev_state_readable,
            )
    return None


def parse_acme_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["acme_temp"] = LegacyCheckDefinition(
    name="acme_temp",
    parse_function=parse_acme_temp,
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.3.1.3.1.1",
        oids=["3", "4", "5"],
    ),
    service_name="Temperature %s",
    discovery_function=inventory_acme_temp,
    check_function=check_acme_temp,
    check_ruleset_name="temperature",
)
