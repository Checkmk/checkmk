#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, SNMPTree


def inventory_alcatel_timetra_cpu(info):
    yield None, {}


def check_alcatel_timetra_cpu(_no_item, params, info):
    cpu_perc = int(info[0][0])
    return check_cpu_util(cpu_perc, params)


check_info["alcatel_timetra_cpu"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.1.0", "TiMOS"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6527.3.1.2.1.1",
        oids=["1"],
    ),
    service_name="CPU utilization",
    discovery_function=inventory_alcatel_timetra_cpu,
    check_function=check_alcatel_timetra_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (90.0, 95.0)},
)
