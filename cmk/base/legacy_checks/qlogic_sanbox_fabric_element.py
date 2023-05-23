#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import any_of, OIDEnd, SNMPTree, startswith


def inventory_qlogic_sanbox_fabric_element(info):
    inventory = []
    for _fe_status, fe_id in info:
        inventory.append((fe_id, None))
    return inventory


def check_qlogic_sanbox_fabric_element(item, _no_params, info):
    for fe_status, fe_id in info:
        if fe_id == item:
            if fe_status == "1":
                return 0, "Fabric Element %s is online" % fe_id
            if fe_status == "2":
                return 2, "Fabric Element %s is offline" % fe_id
            if fe_status == "3":
                return 1, "Fabric Element %s is testing" % fe_id
            if fe_status == "4":
                return 2, "Fabric Element %s is faulty" % fe_id
            return 3, "Fabric Element %s is in unidentified status %s" % (fe_id, fe_status)

    return 3, "No Fabric Element %s found" % item


check_info["qlogic_sanbox_fabric_element"] = LegacyCheckDefinition(
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.14"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.8"),
    ),
    check_function=check_qlogic_sanbox_fabric_element,
    discovery_function=inventory_qlogic_sanbox_fabric_element,
    service_name="Fabric Element %s",
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.75.1.1.4.1",
        oids=["4", OIDEnd()],
    ),
)
