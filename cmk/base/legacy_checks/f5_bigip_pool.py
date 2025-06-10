#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

import re

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.f5_bigip import DETECT
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree

# Agent / MIB output
# see: 1.3.6.1.4.1.3375.2.2.5.1.2.1
# F5-BIGIP-LOCAL-MIB::ltmPoolName.              8.80.111.111.108.asci_encoded_str = Pool_NMA
# F5-BIGIP-LOCAL-MIB::ltmPoolMemberCnt.         8.80.111.111.108.95.78.77.65 = 2
# F5-BIGIP-LOCAL-MIB::ltmPoolActiveMemberCnt.   8.80.111.111.108.95.78.77.65 = 0


def parse_f5_bigip_pool(string_table):
    parsed = {}
    processed_member_info = False
    for block in string_table:
        if not block:
            continue

        # Member information
        if len(block[0]) == 3 and processed_member_info:
            break

        if len(block[0]) == 3:
            for line in block:
                parsed.setdefault(line[0], {"act_members": 0, "def_members": 0, "down_info": []})
                parsed[line[0]]["act_members"] += int(line[1])
                parsed[line[0]]["def_members"] += int(line[2])
            processed_member_info = True

        # Status information
        elif len(block[0]) == 6:
            for key, val in parsed.items():
                for line in block:
                    if key == line[0]:
                        val["down_info"].append(line)
    return parsed


def inventory_f5_bigip_pool(parsed):
    # inventorize all pools and their member count
    for item in parsed:
        if item != "":
            yield item, {}


def f5_bigip_pool_get_down_members(down_info):
    downs = []
    up_states = ["4", "28"]
    for line in down_info:
        if line[2] not in up_states or line[3] not in up_states or line[4] in ("2", "3", "4", "5"):
            if re.match(r"\/\S*\/\S*", line[5]):
                host = line[5].split("/")[2]
            else:
                host = line[5]
            downs.append(host + ":" + line[1])
    return downs


def check_f5_bigip_pool(item, params, parsed):
    pool_info = parsed.get(item)
    if not pool_info:
        return None

    pool_act_members = pool_info["act_members"]
    pool_def_members = pool_info["def_members"]
    message = "%d of %d members are up" % (pool_act_members, pool_def_members)

    levels = params["levels_lower"]
    state = 0
    if pool_act_members == pool_def_members or not levels or pool_act_members >= levels[0]:
        state = 0
    elif pool_act_members < levels[1]:
        state = 2
        message += f" (warn/crit: {levels[0]}/{levels[1]})"
    elif pool_act_members < levels[0]:
        state = 1
        message += f" (warn/crit: {levels[0]}/{levels[1]})"

    if pool_act_members < pool_def_members:
        downs = f5_bigip_pool_get_down_members(pool_info["down_info"])
        if downs:
            message += ", down/disabled nodes: %s" % ", ".join(downs)
    return state, message


check_info["f5_bigip_pool"] = LegacyCheckDefinition(
    detect=DETECT,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3375.2.2.5.1.2.1",
            oids=["1", "8", "23"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3375.2.2.5.3.2.1",
            oids=["1", "4", "10", "11", "13", "19"],
        ),
    ],
    parse_function=parse_f5_bigip_pool,
    service_name="Load Balancing Pool %s",
    discovery_function=inventory_f5_bigip_pool,
    check_function=check_f5_bigip_pool,
    check_ruleset_name="f5_pools",
    check_default_parameters={"levels_lower": (2, 1)},
)
