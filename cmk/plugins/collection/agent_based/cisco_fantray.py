#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.534 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.535 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.536 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.537 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.538 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.539 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.540 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.541 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.113000534 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.113000535 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.113000536 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.116000534 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.116000535 2
# .1.3.6.1.4.1.9.9.117.1.4.1.1.1.116000536 2

# .1.3.6.1.2.1.47.1.1.1.1.7.10 Fabric [VPC domain:12]
# .1.3.6.1.2.1.47.1.1.1.1.7.22 Nexus 56128P Supervisor in Fixed Module-1
# .1.3.6.1.2.1.47.1.1.1.1.7.23 24 ports 10GE SFP+ and 2xQSFP ports Ethernet Module
# .1.3.6.1.2.1.47.1.1.1.1.7.149 Nexus 56128P Chassis
# .1.3.6.1.2.1.47.1.1.1.1.7.214 Fixed Slot-1
# .1.3.6.1.2.1.47.1.1.1.1.7.215 Module Slot-2
# .1.3.6.1.2.1.47.1.1.1.1.7.216 Module Slot-3
# .1.3.6.1.2.1.47.1.1.1.1.7.278 PowerSupplyBay-1
# .1.3.6.1.2.1.47.1.1.1.1.7.279 PowerSupplyBay-2
# .1.3.6.1.2.1.47.1.1.1.1.7.280 PowerSupplyBay-3
# .1.3.6.1.2.1.47.1.1.1.1.7.281 PowerSupplyBay-4
# .1.3.6.1.2.1.47.1.1.1.1.7.342 FanBay-1
# .1.3.6.1.2.1.47.1.1.1.1.7.343 FanBay-2
# .1.3.6.1.2.1.47.1.1.1.1.7.344 FanBay-3
# .1.3.6.1.2.1.47.1.1.1.1.7.345 FanBay-4
# .1.3.6.1.2.1.47.1.1.1.1.7.470 PowerSupply-1
# .1.3.6.1.2.1.47.1.1.1.1.7.471 PowerSupply-2
# .1.3.6.1.2.1.47.1.1.1.1.7.472 PowerSupply-3
# .1.3.6.1.2.1.47.1.1.1.1.7.473 PowerSupply-4
# .1.3.6.1.2.1.47.1.1.1.1.7.534 FanModule-1
# .1.3.6.1.2.1.47.1.1.1.1.7.535 FanModule-2
# .1.3.6.1.2.1.47.1.1.1.1.7.536 FanModule-3
# .1.3.6.1.2.1.47.1.1.1.1.7.537 FanModule-4
# .1.3.6.1.2.1.47.1.1.1.1.7.538 PowerSupply-1 Fan-1
# .1.3.6.1.2.1.47.1.1.1.1.7.539 PowerSupply-1 Fan-2
# .1.3.6.1.2.1.47.1.1.1.1.7.540 PowerSupply-2 Fan-1
# .1.3.6.1.2.1.47.1.1.1.1.7.541 PowerSupply-2 Fan-2
# ...


# mypy: disable-error-code="var-annotated"

from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    not_exists,
    OIDCached,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
)


def parse_cisco_fantray(string_table):
    map_states = {
        "1": (State.UNKNOWN, "unknown"),
        "2": (State.OK, "powered on"),
        "3": (State.CRIT, "powered down"),
        "4": (State.CRIT, "partial failure, needs replacement as soon as possible."),
    }

    ppre_parsed = {}
    for end_oid, oper_state in string_table[0]:
        ppre_parsed.setdefault(
            end_oid, map_states.get(oper_state, (State.UNKNOWN, "unexpected(%s)" % oper_state))
        )

    pre_parsed = {}
    for end_oid, name in string_table[1]:
        if end_oid in ppre_parsed:
            pre_parsed.setdefault(name, [])
            pre_parsed[name].append(ppre_parsed[end_oid])

    parsed = {}
    for name, infos in pre_parsed.items():
        if len(infos) > 1:
            for k, state_info in enumerate(infos):
                parsed["%s-%d" % (name, k + 1)] = state_info
        else:
            parsed[name] = infos[0]

    return parsed


def inventory_cisco_fantray(section: Any) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_cisco_fantray(item: str, section: Any) -> CheckResult:
    if item in section:
        state, state_readable = section[item]
        yield Result(state=state, summary="Status: %s" % state_readable)


snmp_section_cisco_fantray = SNMPSection(
    name="cisco_fantray",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"), not_exists(".1.3.6.1.4.1.9.9.13.1.4.1.2.*")
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.117.1.4.1.1",
            oids=[OIDEnd(), "1"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), OIDCached("7")],
        ),
    ],
    parse_function=parse_cisco_fantray,
)
check_plugin_cisco_fantray = CheckPlugin(
    name="cisco_fantray",
    service_name="Fan %s",
    discovery_function=inventory_cisco_fantray,
    check_function=check_cisco_fantray,
)
