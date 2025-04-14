#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.acme.agent_based.lib import ACME_ENVIRONMENT_STATES, DETECT_ACME
from cmk.plugins.lib.elphase import check_elphase

Section = dict[str, tuple[str, str]]

# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.1 MAIN 1.20V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.1
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.2 MAIN 1.50V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.2
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.3 MAIN 1.80V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.3
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.4 MAIN 2.50V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.4
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.5 MAIN 3.30V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.5
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.6 MAIN 5.00V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.6
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.7 MAIN 3.30V AUX --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.7
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.8 PHY 1.20V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.8
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.9 PHY 1.50V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.9
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.10 PHY 1.80V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.10
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.11 PHY 2.50V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.11
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.12 PHY 3.30V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.12
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.13 PHY 1.00V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.13
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.3.14 PHY 3.30V --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusDescr.14
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.1 1199 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.1
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.2 1500 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.2
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.3 1794 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.3
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.4 2513 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.4
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.5 3287 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.5
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.6 4967 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.6
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.7 3258 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.7
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.8 1205 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.8
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.9 1500 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.9
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.10 1800 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.10
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.11 2490 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.11
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.12 3270 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.12
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.13 989 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.13
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.4.14 3318 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageStatusValue.14
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.1 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.1
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.2 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.2
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.3 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.3
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.4 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.4
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.5 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.5
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.6 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.6
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.7 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.7
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.8 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.8
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.9 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.9
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.10 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.10
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.11 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.11
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.12 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.12
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.13 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.13
# .1.3.6.1.4.1.9148.3.3.1.2.1.1.5.14 2 --> ACMEPACKET-ENVMON-MIB::apEnvMonVoltageState.14


def inventory_acme_voltage(section: StringTable) -> DiscoveryResult:
    if section:
        yield from [Service(item=descr) for descr, _value_str, state in section if state != "7"]


def check_acme_voltage(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    value_str, rstate = section[item]
    state, readable = ACME_ENVIRONMENT_STATES[rstate]
    yield from check_elphase(
        item,
        params,
        {item: {"voltage": (float(value_str) / 1000.0, (int(state), readable))}},
    )


def parse_acme_voltage(string_table: StringTable) -> Section | None:
    section: Section = {}
    for descr, value_str, rstate in string_table:
        section[descr] = (value_str, rstate)
    return section or None


snmp_section_acme_voltage = SimpleSNMPSection(
    name="acme_voltage",
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.3.1.2.1.1",
        oids=["3", "4", "5"],
    ),
    parse_function=parse_acme_voltage,
)

check_plugin_acme_voltage = CheckPlugin(
    name="acme_voltage",
    service_name="Voltage %s",
    discovery_function=inventory_acme_voltage,
    check_function=check_acme_voltage,
    check_ruleset_name="el_inphase",
    check_default_parameters={},
)
