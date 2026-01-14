#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def discover_mailman_lists(info):
    return [(i[0], None) for i in info]


def check_mailman_lists(item, params, info):
    for line in info:
        name, num_members = line[0], saveint(line[1])
        if name == item:
            return (0, "%d members subscribed" % (num_members), [("count", num_members)])
    return (3, "List could not be found in agent output")


def parse_mailman_lists(string_table: StringTable) -> StringTable:
    return string_table


check_info["mailman_lists"] = LegacyCheckDefinition(
    name="mailman_lists",
    parse_function=parse_mailman_lists,
    service_name="Mailinglist %s",
    discovery_function=discover_mailman_lists,
    check_function=check_mailman_lists,
)
