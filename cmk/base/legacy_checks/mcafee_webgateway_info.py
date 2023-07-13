#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils import mcafee_gateway


def inventory_mcafee_webgateway_info(info):
    if info:
        return [(None, None)]
    return []


def check_mcafee_webgateway_info(_no_item, _no_params, info):
    version, revision = info[0]
    return 0, "Product version: %s, Revision: %s" % (version, revision)


check_info["mcafee_webgateway_info"] = LegacyCheckDefinition(
    detect=mcafee_gateway.DETECT_WEB_GATEWAY,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.7.1",
        oids=["3", "9"],
    ),
    service_name="Web gateway info",
    discovery_function=inventory_mcafee_webgateway_info,
    check_function=check_mcafee_webgateway_info,
)
