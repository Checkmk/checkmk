#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<mongodb_instance:sep(9)>>>
# mode secondary
# address 10.1.2.4


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def inventory_mongodb_instance(info):
    return [(None, None)]


def check_mongodb_instance(_no_item, _no_params, info):
    for status, messg in info:
        if status == "error":
            yield 2, messg
        else:
            yield 0, f"{status.title()}: {messg}"


def parse_mongodb_instance(string_table: StringTable) -> StringTable:
    return string_table


check_info["mongodb_instance"] = LegacyCheckDefinition(
    name="mongodb_instance",
    parse_function=parse_mongodb_instance,
    service_name="MongoDB Instance",
    discovery_function=inventory_mongodb_instance,
    check_function=check_mongodb_instance,
)
