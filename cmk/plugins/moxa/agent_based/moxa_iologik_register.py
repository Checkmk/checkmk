#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# "0=Off, 1=On in DI/DO mode or N=Count in DO counter mode"


from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

_STATE_MAP = {0: State.OK, 1: State.WARN}


def discover_iologik_register(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[2]:
            yield Service(item=line[0])


def check_iologik_register(item: str, section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == item:
            val = int(line[2])
            if val in range(2):
                yield Result(state=_STATE_MAP.get(val, State.UNKNOWN), summary=line[1])
            else:
                yield Result(state=State.UNKNOWN, summary=f"Invalid value {line[2]} for register")
            return

    yield Result(state=State.UNKNOWN, summary="Register not found")


def parse_moxa_iologik_register(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_moxa_iologik_register = SimpleSNMPSection(
    name="moxa_iologik_register",
    parse_function=parse_moxa_iologik_register,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8691."),
        startswith(".1.3.6.1.4.1.8691.10.2242.2.0", "E2242-T"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.8691.10.2242.10.4.1.1",
        oids=["1", "2", "3"],
    ),
)

check_plugin_moxa_iologik_register = CheckPlugin(
    name="moxa_iologik_register",
    service_name="Moxa Register %s",
    discovery_function=discover_iologik_register,
    check_function=check_iologik_register,
)

# DIOEntry
# dioIndex Integer32 (0..11)         "The channel dio index."
# dioType Integer32 (0..1)          "The channel dio type. 0=DI, DO=1, AI=2"
# dioMode Integer32 (0..1)          "The channel dio mode. 0=DI, 1=Event Counter"
# dioStatus Unsigned32 (0..4294967295)        "The channel dio(di/do) status. 0=Off, 1=On in DI/DO mode or N=Count in DO counter mode
# dioFilter Integer32 (1..65535) "The channel dio(di) counter filter. unit=0.5ms"
# dioTrigger Integer32 (0..1)        "The channel dio(di) counter trigger level. 0=L2H, 1=H2L"
# dioCntStart Integer32 (0..1)        "The channel dio(do) counter start/stop. 0=stop, 1=start"
# dioPulseStart        Integer32 (0..1) "The channel dio(do) pulse start/stop. 0=stop, 1=start"
# dioPulseONWidth Unsigned32 (1..4294967295) "The channel dio(do) signal ON width. unit=0.5ms"
# dioPulseOFFWidth Unsigned32 (1..4294967295) "The channel dio(do) signal OFF width. unit=0.5ms"
