#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# <<<logins>>>
# 3


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info

logins_default_levels = (20, 30)


def inventory_logins(info):
    if info:
        return [(None, logins_default_levels)]
    return []


def check_logins(_no_item, params, info):
    try:
        logins = int(info[0][0])
    except (IndexError, ValueError):
        return None
    return check_levels(
        logins, "logins", params, infoname="On system", human_readable_func=lambda x: "%d" % x
    )


check_info["logins"] = LegacyCheckDefinition(
    check_function=check_logins,
    discovery_function=inventory_logins,
    service_name="Logins",
    check_ruleset_name="logins",
)
