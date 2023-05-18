#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, get_percent_human_readable, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.fireeye import DETECT

# .1.3.6.1.4.1.25597.13.1.40.0 1


def discover_fireeye_quarantine(string_table):
    if string_table:
        yield None, {}


def check_fireeye_quarantine(_no_item, params, info):
    usage = int(info[0][0])
    return check_levels(
        usage,
        "quarantine",
        params["usage"],
        human_readable_func=get_percent_human_readable,
        infoname="Usage",
    )


check_info["fireeye_quarantine"] = LegacyCheckDefinition(
    detect=DETECT,
    discovery_function=discover_fireeye_quarantine,
    check_function=check_fireeye_quarantine,
    service_name="Quarantine Usage",
    check_ruleset_name="fireeye_quarantine",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.13.1.40",
        oids=["0"],
    ),
    check_default_parameters={"usage": (70, 80)},
)
