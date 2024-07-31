#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.dell import DETECT_OPENMANAGE


def inventory_dell_om_mem(section: StringTable) -> DiscoveryResult:
    yield from [Service(item=x[0]) for x in section]


# DellMemoryDeviceFailureModes                    ::= INTEGER {
#     -- Note: These values are bit masks, so combination values are possible.
#     -- If value is 0 (zero), memory device has no faults.
#     eccSingleBitCorrectionWarningRate(1),       -- ECC single bit correction warning rate exceeded
#     eccSingleBitCorrectionFailureRate(2),       -- ECC single bit correction failure rate exceeded
#     eccMultiBitFault(4),                        -- ECC multibit fault encountered
#     eccSingleBitCorrectionLoggingDisabled(8),   -- ECC single bit correction logging disabled
#     deviceDisabledBySpareActivation(16)         -- device disabled because of spare activation


def check_dell_om_mem(item: str, section: StringTable) -> CheckResult:
    failure_modes = {
        1: "ECC single bit correction warning rate exceeded",
        2: "ECC single bit correction failure rate exceeded",
        4: "ECC multibit fault encountered",
        8: "ECC single bit correction logging disabled",
        16: "device disabled because of spare activation",
    }

    for location, status, size, r_failuremode in section:
        if location == item:
            _status = int(status)
            failuremode = int(r_failuremode)
            if failuremode == 0:
                yield Result(state=State.OK, summary="No failure")
            else:
                bitmask = 1
                while bitmask <= 16:
                    if failuremode & bitmask != 0:
                        if bitmask in [2, 4]:
                            yield Result(state=State.CRIT, summary=failure_modes[bitmask])
                        elif bitmask in [1, 8, 16]:
                            yield Result(state=State.WARN, summary=failure_modes[bitmask])
                    bitmask *= 2

            yield Result(state=State.OK, summary="Size: %s" % render.bytes(int(size) * 1024))


def parse_dell_om_mem(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_dell_om_mem = SimpleSNMPSection(
    name="dell_om_mem",
    detect=DETECT_OPENMANAGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.1.1100.50.1",
        oids=["8.1", "5.1", "14.1", "20.1"],
    ),
    parse_function=parse_dell_om_mem,
)
check_plugin_dell_om_mem = CheckPlugin(
    name="dell_om_mem",
    service_name="Memory Module %s",
    discovery_function=inventory_dell_om_mem,
    check_function=check_dell_om_mem,
)
