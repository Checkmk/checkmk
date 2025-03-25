#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.mcafee_gateway import DETECT_EMAIL_GATEWAY

check_info = {}


def discover_mcafee_emailgateway_av_authentium(section: StringTable) -> DiscoveryResult:
    if section and section[0][0] == "1":
        yield Service()


def check_mcafee_emailgateway_av_authentium(item, params, info):
    map_states = {
        "1": (0, "activated"),
        "0": (1, "deactivated"),
    }

    activated, engine_version, dat_version = info[0]
    state, state_readable = map_states.get(activated, (3, "unknown[%s]" % activated))
    return (
        state,
        f"Status: {state_readable}, Engine version: {engine_version}, DAT version: {dat_version}",
    )


def parse_mcafee_emailgateway_av_authentium(string_table: StringTable) -> StringTable:
    return string_table


check_info["mcafee_emailgateway_av_authentium"] = LegacyCheckDefinition(
    name="mcafee_emailgateway_av_authentium",
    parse_function=parse_mcafee_emailgateway_av_authentium,
    detect=DETECT_EMAIL_GATEWAY,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.4.1.2.3.6",
        oids=["4", "5", "6"],
    ),
    service_name="AV Authentium",
    discovery_function=discover_mcafee_emailgateway_av_authentium,
    check_function=check_mcafee_emailgateway_av_authentium,
)
