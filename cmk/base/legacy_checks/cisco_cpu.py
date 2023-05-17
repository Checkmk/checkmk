#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# oid(".1.3.6.1.4.1.9.9.109.1.1.1.1.5.1") is depreceated by
# oid(".1.3.6.1.4.1.9.9.109.1.1.1.1.8.1"), we recognize both for now


from cmk.base.check_api import (
    all_of,
    any_of,
    check_levels,
    contains,
    exists,
    get_percent_human_readable,
    LegacyCheckDefinition,
    not_contains,
    not_exists,
)
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

factory_settings["cisco_cpu_default_levels"] = {"util": (80.0, 90.0)}


def inventory_cisco_cpu(info):
    if info and (info[0][0].isdigit() or info[0][1].isdigit()):
        yield None, {}


def check_cisco_cpu(item, params, info):
    # Value of info could be (None, None) or ("", "").
    if not info[0][0].isdigit() and not info[0][1].isdigit():
        return 3, "No information about the CPU utilization available"

    if info[0][1]:
        util = float(info[0][1])
    else:
        util = float(info[0][0])

    warn, crit = params.get("util", (None, None)) if isinstance(params, dict) else params

    return check_levels(
        util,
        "util",
        (warn, crit),
        human_readable_func=get_percent_human_readable,
        boundaries=(0, 100),
        infoname="Utilization in the last 5 minutes",
    )


check_info["cisco_cpu"] = LegacyCheckDefinition(
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"),
        any_of(
            not_contains(".1.3.6.1.2.1.1.1.0", "nx-os"), not_exists(".1.3.6.1.4.1.9.9.305.1.1.1.0")
        ),
        not_exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.2.*"),
        any_of(
            exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.8.1"), exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.5.1")
        ),
    ),
    check_function=check_cisco_cpu,
    discovery_function=inventory_cisco_cpu,
    service_name="CPU utilization",
    check_ruleset_name="cpu_utilization",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.109.1.1.1.1",
        oids=["5", "8"],
    ),
    default_levels_variable="cisco_cpu_default_levels",
    check_default_parameters={"util": (80.0, 90.0)},
)
