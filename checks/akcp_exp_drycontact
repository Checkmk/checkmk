#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.akcp_sensor import (
    check_akcp_sensor_drycontact,
    inventory_akcp_sensor_no_params,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.akcp import DETECT_AKCP_EXP

# Example for contents of info
#           description            state  online  critical_desc  normal_desc
# ["Diesel1 Generatorbetrieb",      "2",   "1",        "An",         "Aus"]]

check_info["akcp_exp_drycontact"] = {
    "detect": DETECT_AKCP_EXP,
    "check_function": check_akcp_sensor_drycontact,
    "discovery_function": inventory_akcp_sensor_no_params,
    "service_name": "Dry Contact %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.3854.2.3.4.1",
        oids=["2", "6", "46", "48", "8"],
    ),
}
