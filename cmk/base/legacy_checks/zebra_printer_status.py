#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.config import check_info

from cmk.agent_based.v2 import contains, SNMPTree, StringTable


def inventory_zebra_printer_status(info):
    if info[0][0]:
        return [(None, {})]
    return []


def check_zebra_printer_status(item, params, info):
    zebra_status = saveint(info[0][0])

    if zebra_status == 3:
        return 0, "Printer is online and ready for the next print job"
    if zebra_status == 4:
        return 0, "Printer is printing"
    if zebra_status == 5:
        return 0, "Printer is warming up"
    if zebra_status == 1:
        return 2, "Printer is offline"
    return 3, "Unknown printer status"


def parse_zebra_printer_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["zebra_printer_status"] = LegacyCheckDefinition(
    parse_function=parse_zebra_printer_status,
    detect=contains(".1.3.6.1.2.1.1.1.0", "zebra"),
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.25.3.5.1.1",
        oids=["1"],
    ),
    service_name="Zebra Printer Status",
    discovery_function=inventory_zebra_printer_status,
    check_function=check_zebra_printer_status,
)
