#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import check_levels, get_bytes_human_readable, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    all_of,
    exists,
    get_rate,
    get_value_store,
    SNMPTree,
    startswith,
)


def check_netapp_fcpio(item, params, info):
    read, write = map(int, info[0])
    this_time = int(time.time())
    avg_read = get_rate(
        get_value_store(), "netapp_fcpio.read", this_time, read, raise_overflow=True
    )
    avg_write = get_rate(
        get_value_store(), "netapp_fcpio.write", this_time, write, raise_overflow=True
    )

    yield check_levels(
        avg_read,
        "read",
        params.get("read"),
        human_readable_func=get_bytes_human_readable,
        infoname="Read",
    )

    yield check_levels(
        avg_write,
        "write",
        params.get("write"),
        human_readable_func=get_bytes_human_readable,
        infoname="Write",
    )


check_info["netapp_fcpio"] = LegacyCheckDefinition(
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "NetApp Release"), exists(".1.3.6.1.4.1.789.1.17.20.0")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.789.1.17",
        oids=["20", "21"],
    ),
    service_name="FCP I/O",
    discovery_function=lambda info: [(None, {})],
    check_function=check_netapp_fcpio,
    check_ruleset_name="netapp_fcportio",
    check_default_parameters={},
)
