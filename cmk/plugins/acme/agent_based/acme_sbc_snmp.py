#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.acme.agent_based.lib import DETECT_ACME

# comNET GmbH, Fabian Binder

# .1.3.6.1.4.1.9148.3.2.1.1.3 Health Score (apSysHealthScore)
# .1.3.6.1.4.1.9148.3.2.1.1.4 Health Status Description (apSysRedundancy)


class ParamsT(TypedDict):
    lower_levels: LevelsT


@dataclass(frozen=True)
class Section:
    score: str
    status: str


def parse_acme_sbc_snmp(string_table: StringTable) -> Section | None:
    if string_table:
        return Section(
            score=string_table[0][1],
            status=string_table[1][1],
        )
    return None


snmp_section_acme_sbc_snmp = SimpleSNMPSection(
    name="acme_sbc_snmp",
    detect=DETECT_ACME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9148.3.2.1.1",
        oids=["3", "4"],
    ),
    parse_function=parse_acme_sbc_snmp,
)


def discover_acme_sbc_snmp(section: Section) -> DiscoveryResult:
    yield Service()


def check_acme_sbc_snmp(params: ParamsT, section: Section) -> CheckResult:
    map_states = {
        "0": (3, "unknown"),
        "1": (1, "initial"),
        "2": (0, "active"),
        "3": (0, "standby"),
        "4": (2, "out of service"),
        "5": (2, "unassigned"),
        "6": (1, "active (pending)"),
        "7": (1, "standby (pending)"),
        "8": (1, "out of service (pending)"),
        "9": (1, "recovery"),
    }

    health_state, health_state_readable = map_states.get(section.status, (3, "unknown"))
    yield Result(state=State(health_state), summary="Health state: %s" % (health_state_readable))

    yield from check_levels(
        int(section.score),
        levels_lower=params["lower_levels"],
        metric_name="health_state",
        label="Score",
        render_func=lambda v: f"{v}%",
    )


check_plugin_acme_sbc_snmp = CheckPlugin(
    name="acme_sbc_snmp",
    service_name="ACME SBC health",
    discovery_function=discover_acme_sbc_snmp,
    check_function=check_acme_sbc_snmp,
    check_ruleset_name="acme_sbc_snmp",
    check_default_parameters=ParamsT(lower_levels=("fixed", (75, 50))),
)
