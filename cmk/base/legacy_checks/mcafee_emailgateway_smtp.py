#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import get_bytes_human_readable, LegacyCheckDefinition
from cmk.base.check_legacy_includes.mcafee_gateway import inventory_mcafee_gateway_generic
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.mcafee_gateway import DETECT_EMAIL_GATEWAY

# TODO params?


def check_mcafee_emailgateway_smtp(item, params, info):
    total_connections, total_bytes, kernel_mode_blocked, kernel_mode_active = map(int, info[0])
    return 0, "Total connections: %s (%s), Kernel blocked: %s, Kernel active: %s" % (
        total_connections,
        get_bytes_human_readable(total_bytes),
        kernel_mode_blocked,
        kernel_mode_active,
    )


check_info["mcafee_emailgateway_smtp"] = LegacyCheckDefinition(
    detect=DETECT_EMAIL_GATEWAY,
    discovery_function=inventory_mcafee_gateway_generic,
    check_function=check_mcafee_emailgateway_smtp,
    service_name="SMTP",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.4.1.2.3.3",
        oids=["1", "2", "3", "4"],
    ),
)
