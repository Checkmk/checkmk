# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, Mapping

from .agent_based_api.v1 import register, Result, Service, SNMPTree
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.ciena_ces import DETECT_CIENA_5171
from .utils.ciena_ces import OperStateSection as Section
from .utils.ciena_ces import parse_ciena_oper_state


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
        state=state.OK if section[item].name == params["discovered_oper_state"] else state.CRIT,
        summary=f"CFM-Service instance is {section[item].name}",
    )


register.snmp_section(
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

register.check_plugin(
    name="ciena_cfm",
    service_name="CFM-Service %s",
    discovery_function=discover_ciena_cfm,
    check_function=check_ciena_cfm,
    check_default_parameters={},
)
