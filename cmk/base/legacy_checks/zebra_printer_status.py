#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, SNMPTree


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


check_info["zebra_printer_status"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.1.0", "zebra"),
    check_function=check_zebra_printer_status,
    discovery_function=inventory_zebra_printer_status,
    service_name="Zebra Printer Status",
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.25.3.5.1.1",
        oids=["1"],
    ),
)
