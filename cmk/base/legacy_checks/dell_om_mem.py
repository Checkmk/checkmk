#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.plugins.lib.dell import DETECT_OPENMANAGE


def inventory_dell_om_mem(info):
    return [(x[0], None) for x in info]


# DellMemoryDeviceFailureModes                    ::= INTEGER {
#     -- Note: These values are bit masks, so combination values are possible.
#     -- If value is 0 (zero), memory device has no faults.
#     eccSingleBitCorrectionWarningRate(1),       -- ECC single bit correction warning rate exceeded
#     eccSingleBitCorrectionFailureRate(2),       -- ECC single bit correction failure rate exceeded
#     eccMultiBitFault(4),                        -- ECC multibit fault encountered
#     eccSingleBitCorrectionLoggingDisabled(8),   -- ECC single bit correction logging disabled
#     deviceDisabledBySpareActivation(16)         -- device disabled because of spare activation


def check_dell_om_mem(item, _no_params, info):
    failure_modes = {
        1: "ECC single bit correction warning rate exceeded",
        2: "ECC single bit correction failure rate exceeded",
        4: "ECC multibit fault encountered",
        8: "ECC single bit correction logging disabled",
        16: "device disabled because of spare activation",
    }

    for location, status, size, failuremode in info:
        if location == item:
            status = int(status)
            failuremode = int(failuremode)
            if failuremode == 0:
                yield 0, "No failure"
            else:
                bitmask = 1
                while bitmask <= 16:
                    if failuremode & bitmask != 0:
                        if bitmask in [2, 4]:
                            yield 2, failure_modes[bitmask]
                        elif bitmask in [1, 8, 16]:
                            yield 1, failure_modes[bitmask]
                    bitmask *= 2

            yield 0, "Size: %s" % render.bytes(int(size) * 1024)


def parse_dell_om_mem(string_table: StringTable) -> StringTable:
    return string_table


check_info["dell_om_mem"] = LegacyCheckDefinition(
    parse_function=parse_dell_om_mem,
    detect=DETECT_OPENMANAGE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.1.1100.50.1",
        oids=["8.1", "5.1", "14.1", "20.1"],
    ),
    service_name="Memory Module %s",
    discovery_function=inventory_dell_om_mem,
    check_function=check_dell_om_mem,
)
