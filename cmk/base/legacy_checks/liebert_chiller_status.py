#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import startswith
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree


def inventory_liebert_chiller_status(info):
    return [(None, None)]


def check_liebert_chiller_status(_no_item, _no_params, info):
    status = info[0][0]
    if status not in ["5", "7"]:
        return 2, "Device is in a non OK state"
    return 0, "Device is in a OK state"


check_info["liebert_chiller_status"] = {
    "detect": startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.476.1.42.4.3.20"),
    "check_function": check_liebert_chiller_status,
    "discovery_function": inventory_liebert_chiller_status,
    "service_name": "Chiller status",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.4.3.20.1.1.20",
        oids=["2"],
    ),
}
