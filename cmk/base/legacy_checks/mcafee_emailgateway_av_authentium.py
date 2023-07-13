#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.mcafee_gateway import DETECT_EMAIL_GATEWAY


def inventory_mcafee_emailgateway_av_authentium(info):
    if info[0][0] == "1":
        return [(None, {})]
    return []


def check_mcafee_emailgateway_av_authentium(item, params, info):
    map_states = {
        "1": (0, "activated"),
        "0": (1, "deactivated"),
    }

    activated, engine_version, dat_version = info[0]
    state, state_readable = map_states.get(activated, (3, "unknown[%s]" % activated))
    return state, "Status: %s, Engine version: %s, DAT version: %s" % (
        state_readable,
        engine_version,
        dat_version,
    )


check_info["mcafee_emailgateway_av_authentium"] = LegacyCheckDefinition(
    detect=DETECT_EMAIL_GATEWAY,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.4.1.2.3.6",
        oids=["4", "5", "6"],
    ),
    service_name="AV Authentium",
    discovery_function=inventory_mcafee_emailgateway_av_authentium,
    check_function=check_mcafee_emailgateway_av_authentium,
)
