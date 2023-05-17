#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# MIB structure:
# 1.3.6.1.4.1.52.4.3.1.2.1.1.1    ctChasPowerSupplyNum
# 1.3.6.1.4.1.52.4.3.1.2.1.1.2    ctChasPowerSupplyState
# 1.3.6.1.4.1.52.4.3.1.2.1.1.3    ctChasPowerSupplyType
# 1.3.6.1.4.1.52.4.3.1.2.1.1.4    ctChasPowerSupplyRedundancy


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.enterasys import DETECT_ENTERASYS

factory_settings["enterasys_powersupply_default"] = {
    "redundancy_ok_states": [
        1,
    ],
}


def inventory_enterasys_powersupply(info):
    inventory = []
    for num, state, _typ, _redun in info:
        if state == "3":
            inventory.append((num, {}))
    return inventory


def check_enterasys_powersupply(item, params, info):
    supply_types = {
        "1": "ac-dc",
        "2": "dc-dc",
        "3": "notSupported",
        "4": "highOutput",
    }
    redundancy_types = {
        "1": "redundant",
        "2": "notRedundant",
        "3": "notSupported",
    }

    for num, state, typ, redun in info:
        if num == item:
            if state == "4":
                return 2, "Status: installed and not operating"

            redun_mapped = redundancy_types.get(redun, "unknown[%s]" % redun)
            if redun and int(redun) in params["redundancy_ok_states"]:
                return 0, "Status: working and %s (%s)" % (
                    redun_mapped,
                    supply_types.get(typ, "unknown[%s]" % typ),
                )
            return 1, "Status: %s" % redun_mapped
    return None


check_info["enterasys_powersupply"] = LegacyCheckDefinition(
    detect=DETECT_ENTERASYS,
    check_function=check_enterasys_powersupply,
    discovery_function=inventory_enterasys_powersupply,
    service_name="PSU %s",
    default_levels_variable="enterasys_powersupply_default",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.52.4.3.1.2.1.1",
        oids=[OIDEnd(), "2", "3", "4"],
    ),
    check_ruleset_name="enterasys_powersupply",
    check_default_parameters={
        "redundancy_ok_states": [
            1,
        ],
    },
)
