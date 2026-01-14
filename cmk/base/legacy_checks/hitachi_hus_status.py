#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable

check_info = {}


def discover_hitachi_hus_status(info):
    return [(None, None)]


def check_hitachi_hus_status(_no_item, _no_params, info):
    status_values = {
        0: (0, "Array in normal status"),
        1: (2, "Drive blocked"),
        2: (2, "Spare drive blockade"),
        4: (2, "Data drive blockade"),
        8: (1, "ENC alarm"),
        64: (1, "Warned array"),
        128: (2, "Mate controller blocked"),
        256: (2, "UPS alarm"),
        1024: (2, "Path blocked"),
        16384: (2, "Drive I/O module failure"),
        32768: (2, "Controller failure by related parts"),
        65536: (1, "Battery alarm"),
        131072: (2, "Power supply failure"),
        1048576: (1, "Fan alarm"),
        4194304: (2, "Host I/O module failure"),
        8388608: (2, "Management module failure"),
        16777216: (2, "Host connector alarm"),
        268435456: (2, "Host connector alarm"),
    }
    if int(info[0][0]) == 0:
        yield 0, "Array in normal status"
    else:
        yield 0, "Errorcode: %s" % info[0][0]
        for status, output in status_values.items():
            state, message = output
            if status & int(info[0][0]):
                yield state, message


def parse_hitachi_hus_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["hitachi_hus_status"] = LegacyCheckDefinition(
    name="hitachi_hus_status",
    parse_function=parse_hitachi_hus_status,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.116"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.116.5.11.1.2.2",
        oids=["1"],
    ),
    service_name="Status",
    discovery_function=discover_hitachi_hus_status,
    check_function=check_hitachi_hus_status,
)
