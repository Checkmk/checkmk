#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree, startswith


def bintec_brrp_status_compose_item(brrp_id):
    return re.sub(r"\..*", "", brrp_id)


def inventory_bintec_brrp_status(info):
    inventory = []
    for brrp_id, _brrp_status in info:
        inventory.append((bintec_brrp_status_compose_item(brrp_id), None))
    return inventory


def check_bintec_brrp_status(item, _no_params, info):
    for brrp_id, brrp_status in info:
        brrp_id = bintec_brrp_status_compose_item(brrp_id)
        if brrp_id == item:
            if brrp_status == "1":
                message = "Status for %s is initialize" % brrp_id
                status = 1
            elif brrp_status == "2":
                message = "Status for %s is backup" % brrp_id
                status = 0
            elif brrp_status == "3":
                message = "Status for %s is master" % brrp_id
                status = 0
            else:
                message = "Status for %s is at unknown value %s" % (brrp_id, brrp_status)
                status = 3

            return status, message

    return 3, "Status for %s not found" % item


check_info["bintec_brrp_status"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.272.4"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.272.4.40.1.1",
        oids=[OIDEnd(), "4"],
    ),
    service_name="BRRP Status %s",
    discovery_function=inventory_bintec_brrp_status,
    check_function=check_bintec_brrp_status,
)
