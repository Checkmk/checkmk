#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.plugins.huawei.lib import DETECT_HUAWEI_SWITCH

check_info = {}

huawei_switch_stack_unknown_role = "unknown"


def parse_huawei_switch_stack(string_table):
    stack_role_names = {
        "1": "master",
        "2": "standby",
        "3": "slave",
    }

    stack_enabled_info, stack_role_info = string_table
    if not stack_enabled_info or stack_enabled_info[0][0] != "1":
        return {}

    parsed = {}
    for line in stack_role_info:
        member_number = line[0]
        stack_role = stack_role_names.get(line[1], huawei_switch_stack_unknown_role)
        parsed[member_number] = stack_role

    return parsed


def discover_huawei_switch_stack(parsed):
    for item, role in parsed.items():
        yield (item, {"expected_role": role})


def check_huawei_switch_stack(item, params, parsed):
    if not (item_data := parsed.get(item)):
        return

    if item_data == huawei_switch_stack_unknown_role:
        yield 2, item_data

    elif item_data == params["expected_role"]:
        yield 0, item_data

    else:
        yield 2, "Unexpected role: {} (Expected: {})".format(item_data, params["expected_role"])


check_info["huawei_switch_stack"] = LegacyCheckDefinition(
    name="huawei_switch_stack",
    detect=DETECT_HUAWEI_SWITCH,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2011.5.25.183.1",
            oids=["5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2011.5.25.183.1.20.1",
            oids=[OIDEnd(), "3"],
        ),
    ],
    parse_function=parse_huawei_switch_stack,
    service_name="Stack role %s",
    discovery_function=discover_huawei_switch_stack,
    check_function=check_huawei_switch_stack,
)
