#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<acme_sbc>>>
# show health
#         Media Synchronized            true
#         SIP Synchronized              true
#         BGF Synchronized              disabled
#         MGCP Synchronized             disabled
#         H248 Synchronized             disabled
#         Config Synchronized           true
#         Collect Synchronized          disabled
#         Radius CDR Synchronized       disabled
#         Rotated CDRs Synchronized     disabled
#         IPSEC Synchronized            disabled
#         Iked Synchronized             disabled
#         Active Peer Address           179.253.2.2
#
# Redundancy Protocol Process (v3):
#         State                           Standby
#         Health                          100
#         Lowest Local Address            189.253.3.1:9090
#         1 peer(s) on 2 socket(s):
#         BERTZSBC02: v3, Active, health=100, max silence=1050
#                    last received from 142.224.2.3 on wancom1:0
#
#         Switchover log:
#         Apr 24 10:14:09.235: Standby to BecomingActive, active peer xxx has timed out, no arp reply from active in 250ms
#         Oct 17 10:07:44.567: Active to RelinquishingActive
#         Oct 20 18:41:11.855: Standby to BecomingActive, active peer xxx has unacceptable health (70)
#         Oct 29 11:46:04.294: Active to RelinquishingActive
#         Oct 29 11:47:05.452: Standby to BecomingActive, active peer xxx has unacceptable health (70)
#         Dec  8 11:37:36.445: Active to RelinquishingActive
#         Dec  8 11:43:00.227: Standby to BecomingActive, active peer xxx has timed out, no arp reply from active in 250ms
#         Mar 16 10:13:33.248: Active to RelinquishingActive

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

Section = tuple[Mapping[str, str], Mapping[str, str]]


def acme_sbc_parse_function(string_table: StringTable) -> Section:
    states = {}
    settings = {}
    for line in string_table:
        if len(line) == 2:
            for what in ["Health", "State"]:
                if line[0] == what:
                    states[what] = line[1]
        elif len(line) == 3 and line[1] == "Synchronized":
            settings[line[0]] = line[2]
    return states, settings


def inventory_acme_sbc(section: Section) -> DiscoveryResult:
    yield Service()


def check_acme_sbc(section: Section) -> CheckResult:
    health = int(section[0]["Health"])
    dev_state = section[0]["State"]
    if health == 100:
        state = State.OK
    else:
        state = State.CRIT
    yield Result(state=state, summary="Health at %d %% (State: %s)" % (health, dev_state))


agent_section_acme_sbc = AgentSection(
    name="acme_sbc",
    parse_function=acme_sbc_parse_function,
)

check_plugin_acme_sbc = CheckPlugin(
    name="acme_sbc",
    service_name="Status",
    discovery_function=inventory_acme_sbc,
    check_function=check_acme_sbc,
)


def inventory_acme_sbc_settings(section: Section) -> DiscoveryResult:
    yield Service(parameters=section[1])


def check_acme_sbc_settings(params: Mapping[str, Any], section: Section) -> CheckResult:
    current_settings = section[1]
    saved_settings = params
    yield Result(state=State.OK, summary="Checking %d settings" % len(saved_settings))
    for setting, value in saved_settings.items():
        if current_settings[setting] != value:
            yield Result(
                state=State.CRIT,
                summary=f"{setting} changed from {value} to {current_settings[setting]}",
            )


check_plugin_acme_sbc_settings = CheckPlugin(
    name="acme_sbc_settings",
    service_name="Settings",
    sections=["acme_sbc"],
    discovery_function=inventory_acme_sbc_settings,
    check_function=check_acme_sbc_settings,
    check_default_parameters={},
)
