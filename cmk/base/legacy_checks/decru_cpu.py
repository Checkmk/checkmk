#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.decru import DETECT_DECRU


def inventory_decru_cpu(info):
    if len(info) == 5:
        return [(None, None)]
    return []


def check_decru_cpu(item, _no_params, info):
    user, nice, system, interrupt, idle = [float(x[0]) / 10.0 for x in info]
    user += nice

    perfdata = [
        ("user", "%.3f" % user),
        ("system", "%.3f" % system),
        ("interrupt", "%.3f" % interrupt),
    ]

    return (
        0,
        "user %.0f%%, sys %.0f%%, interrupt %.0f%%, idle %.0f%%" % (user, system, interrupt, idle),
        perfdata,
    )


check_info["decru_cpu"] = LegacyCheckDefinition(
    detect=DETECT_DECRU,
    check_function=check_decru_cpu,
    discovery_function=inventory_decru_cpu,
    service_name="CPU utilization",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12962.1.1",
        oids=["8"],
    ),
)
