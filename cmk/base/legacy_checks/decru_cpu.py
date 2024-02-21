#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.decru import DETECT_DECRU


def inventory_decru_cpu(info):
    if len(info) == 5:
        return [(None, None)]
    return []


def check_decru_cpu(item, _no_params, info):
    user, nice, system, interrupt, idle = (float(x[0]) / 10.0 for x in info)
    user += nice

    perfdata = [
        ("user", "%.3f" % user),
        ("system", "%.3f" % system),
        ("interrupt", "%.3f" % interrupt),
    ]

    return (
        0,
        f"user {user:.0f}%, sys {system:.0f}%, interrupt {interrupt:.0f}%, idle {idle:.0f}%",
        perfdata,
    )


def parse_decru_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["decru_cpu"] = LegacyCheckDefinition(
    parse_function=parse_decru_cpu,
    detect=DETECT_DECRU,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12962.1.1",
        oids=["8"],
    ),
    service_name="CPU utilization",
    discovery_function=inventory_decru_cpu,
    check_function=check_decru_cpu,
)
