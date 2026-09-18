#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.mcafee.libgateway import DETECT_EMAIL_GATEWAY


def parse_mcafee_emailgateway_av_authentium(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_mcafee_emailgateway_av_authentium(section: StringTable) -> DiscoveryResult:
    if section and section[0][0] == "1":
        yield Service()


def check_mcafee_emailgateway_av_authentium(section: StringTable) -> CheckResult:
    map_states = {
        "1": (State.OK, "activated"),
        "0": (State.WARN, "deactivated"),
    }

    activated, engine_version, dat_version = section[0]
    state, state_readable = map_states.get(activated, (State.UNKNOWN, f"unknown[{activated}]"))
    yield Result(
        state=state,
        summary=(
            f"Status: {state_readable}, Engine version: {engine_version}, "
            f"DAT version: {dat_version}"
        ),
    )


snmp_section_mcafee_emailgateway_av_authentium = SimpleSNMPSection(
    name="mcafee_emailgateway_av_authentium",
    detect=DETECT_EMAIL_GATEWAY,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.4.1.2.3.6",
        oids=["4", "5", "6"],
    ),
    parse_function=parse_mcafee_emailgateway_av_authentium,
)


check_plugin_mcafee_emailgateway_av_authentium = CheckPlugin(
    name="mcafee_emailgateway_av_authentium",
    service_name="AV Authentium",
    discovery_function=discover_mcafee_emailgateway_av_authentium,
    check_function=check_mcafee_emailgateway_av_authentium,
)
