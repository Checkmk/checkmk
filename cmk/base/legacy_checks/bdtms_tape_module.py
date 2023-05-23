#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, OIDEnd, SNMPTree


def inventory_bdtms_tape_module(info):
    for device in info:
        device_id = device[0]
        yield (device_id, None)


def check_bdtms_tape_module(item, _no_params, info):
    def state(status):
        return 0 if status.lower() == "ok" else 2

    for device in info:
        device_id, module_status, board_status, power_status = device
        if device_id != item:
            continue

        yield state(module_status), "Module: %s" % module_status.lower()
        yield state(board_status), "Board: %s" % board_status.lower()
        yield state(power_status), "Power supply: %s" % power_status.lower()


check_info["bdtms_tape_module"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.20884.77.83.1"),
    discovery_function=inventory_bdtms_tape_module,
    check_function=check_bdtms_tape_module,
    service_name="Tape Library Module %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.20884.2.4.1",
        oids=[OIDEnd(), "4", "5", "6"],
    ),
)
