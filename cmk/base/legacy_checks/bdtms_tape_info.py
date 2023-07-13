#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, SNMPTree


def inventory_bdtms_tape_info(info):
    return [(None, None)]


def check_bdtms_tape_info(_no_item, _no_params, info):
    for name, value in zip(["Vendor", "Product ID", "Serial Number", "Software Revision"], info[0]):
        yield 0, "%s: %s" % (name, value)


check_info["bdtms_tape_info"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20884.77.83.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20884.1",
        oids=["1", "2", "3", "4"],
    ),
    service_name="Tape Library Info",
    discovery_function=inventory_bdtms_tape_info,
    check_function=check_bdtms_tape_info,
)
