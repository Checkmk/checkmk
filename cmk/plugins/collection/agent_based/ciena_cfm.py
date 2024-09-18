#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
)
from cmk.plugins.lib.ciena_ces import DETECT_CIENA_5171, parse_ciena_oper_state
from cmk.plugins.lib.ciena_ces import OperStateSection as Section


def discover_ciena_cfm(section: Section) -> DiscoveryResult:
    yield from (
        Service(item=item, parameters={"discovered_oper_state": oper_state.name})
        for item, oper_state in section.items()
    )


def check_ciena_cfm(
    item: str,
    params: Mapping[Literal["discovered_oper_state"], str],
    section: Section,
) -> CheckResult:
    if item not in section:
        return
    yield Result(
        state=State.OK if section[item].name == params["discovered_oper_state"] else State.CRIT,
        summary=f"CFM-Service instance is {section[item].name}",
    )


snmp_section_ciena_cfm = SimpleSNMPSection(
    name="ciena_cfm",
    parse_function=parse_ciena_oper_state,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1271.2.1.4.1.2.1.1",
        oids=[
            "6",  # cienaCesCfmServiceName
            "5",  # cienaCesCfmServiceOperState
        ],
    ),
    detect=DETECT_CIENA_5171,
)

check_plugin_ciena_cfm = CheckPlugin(
    name="ciena_cfm",
    service_name="CFM-Service %s",
    discovery_function=discover_ciena_cfm,
    check_function=check_ciena_cfm,
    check_default_parameters={},
)
