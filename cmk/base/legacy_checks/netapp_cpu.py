#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import all_of, exists, LegacyCheckDefinition, startswith
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree


def check_netapp_cpu(item, params, info):
    util = float(info[0][0])
    return check_cpu_util(util, params)


check_info["netapp_cpu"] = LegacyCheckDefinition(
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.1.0", "NetApp Release"), exists(".1.3.6.1.4.1.789.1.2.1.3.0")
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.789.1.2.1",
        oids=["3"],
    ),
    service_name="CPU utilization",
    discovery_function=lambda info: [(None, {})],
    check_function=check_netapp_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
