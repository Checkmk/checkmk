#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from itertools import cycle

from cmk.base.check_legacy_includes.elphase import check_elphase

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree

check_info = {}

# .1.3.6.1.4.1.705.2.3.2.1.2.1 3997 --> MG-SNMP-STS-MIB::stsmgSource1PhasePhaseVoltage.1
# .1.3.6.1.4.1.705.2.3.2.1.2.2 4017 --> MG-SNMP-STS-MIB::stsmgSource1PhasePhaseVoltage.2
# .1.3.6.1.4.1.705.2.3.2.1.2.3 4012 --> MG-SNMP-STS-MIB::stsmgSource1PhasePhaseVoltage.3
# .1.3.6.1.4.1.705.2.3.2.1.3.1 0 --> MG-SNMP-STS-MIB::stsmgSource1Current.1
# .1.3.6.1.4.1.705.2.3.2.1.3.2 0 --> MG-SNMP-STS-MIB::stsmgSource1Current.2
# .1.3.6.1.4.1.705.2.3.2.1.3.3 0 --> MG-SNMP-STS-MIB::stsmgSource1Current.3
# .1.3.6.1.4.1.705.2.3.2.1.4.1 0 --> MG-SNMP-STS-MIB::stsmgSource1ActivePower.1
# .1.3.6.1.4.1.705.2.3.2.1.4.2 0 --> MG-SNMP-STS-MIB::stsmgSource1ActivePower.2
# .1.3.6.1.4.1.705.2.3.2.1.4.3 0 --> MG-SNMP-STS-MIB::stsmgSource1ActivePower.3
# .1.3.6.1.4.1.705.2.3.16.0 499 --> MG-SNMP-STS-MIB::stsmgSource1Frequency.0

#
#
# .1.3.6.1.4.1.705.2.4.2.1.2.1 3946 --> MG-SNMP-STS-MIB::stsmgSource2PhasePhaseVoltage.1
# .1.3.6.1.4.1.705.2.4.2.1.2.2 3970 --> MG-SNMP-STS-MIB::stsmgSource2PhasePhaseVoltage.2
# .1.3.6.1.4.1.705.2.4.2.1.2.3 3955 --> MG-SNMP-STS-MIB::stsmgSource2PhasePhaseVoltage.3
# .1.3.6.1.4.1.705.2.4.2.1.3.1 170 --> MG-SNMP-STS-MIB::stsmgSource2Current.1
# .1.3.6.1.4.1.705.2.4.2.1.3.2 155 --> MG-SNMP-STS-MIB::stsmgSource2Current.2
# .1.3.6.1.4.1.705.2.4.2.1.3.3 146 --> MG-SNMP-STS-MIB::stsmgSource2Current.3
# .1.3.6.1.4.1.705.2.4.2.1.4.1 3700 --> MG-SNMP-STS-MIB::stsmgSource2ActivePower.1
# .1.3.6.1.4.1.705.2.4.2.1.4.2 3500 --> MG-SNMP-STS-MIB::stsmgSource2ActivePower.2
# .1.3.6.1.4.1.705.2.4.2.1.4.3 3300 --> MG-SNMP-STS-MIB::stsmgSource2ActivePower.3
# .1.3.6.1.4.1.705.2.4.16.0 499 --> MG-SNMP-STS-MIB::stsmgSource2Frequency.0


def parse_apc_sts_inputs(string_table):
    return {
        f"Source {src} Phase {phs}": {
            "voltage": int(voltage) / 10.0,
            "current": int(current) / 10.0,
            "power": int(power),
        }
        for src, block in enumerate(string_table, 1)
        for (voltage, current, power), phs in zip(block, cycle((1, 2, 3)))
    }


def discover_apc_sts_inputs(section):
    yield from ((item, {}) for item in section)


check_info["apc_sts_inputs"] = LegacyCheckDefinition(
    name="apc_sts_inputs",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.705.2.2"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.705.2.3.2.1",
            oids=["2", "3", "4"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.705.2.4.2.1",
            oids=["2", "3", "4"],
        ),
    ],
    parse_function=parse_apc_sts_inputs,
    service_name="Input %s",
    discovery_function=discover_apc_sts_inputs,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
