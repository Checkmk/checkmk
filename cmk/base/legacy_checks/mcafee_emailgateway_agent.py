#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.mcafee_gateway import inventory_mcafee_gateway_generic
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.mcafee_gateway import DETECT_EMAIL_GATEWAY

# TODO together with 'mcafee_emailgateway_av_mcafee'
# only info check?


def check_mcafee_emailgateway_agent(item, params, info):
    return 0, "Version: %s, Hostname: %s, Last file update: %s" % tuple(info[0])


check_info["mcafee_emailgateway_agent"] = LegacyCheckDefinition(
    detect=DETECT_EMAIL_GATEWAY,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.4.1.2.1.1",
        oids=["1", "2", "3"],
    ),
    service_name="Agent Info",
    discovery_function=inventory_mcafee_gateway_generic,
    check_function=check_mcafee_emailgateway_agent,
)
