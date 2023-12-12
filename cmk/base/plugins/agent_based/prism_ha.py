#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.plugins.lib.prism import load_json

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Mapping[str, Mapping[str, Any]]


def parse_prism_ha(string_table: StringTable) -> Section:
    return load_json(string_table)


register.agent_section(
    name="prism_ha",
    parse_function=parse_prism_ha,
)


def discovery_prism_ha(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_prism_ha(section: Section) -> CheckResult:
    if not section:
        return

    _HA_STATES = {
        "HIGHLY_AVAILABLE": 0,
        "HighlyAvailable": 0,
        "HEALING": 1,
        "Healing": 1,
        "BEST_EFFORT": 0,
        "BestEffort": 0,
        "DISABLED": 2,
        "Disabled": 2,
    }
    state = 0
    if section.get("failover_enabled"):
        state = _HA_STATES.get(str(section.get("ha_state")), 3)

    yield Result(state=State(state), summary=f"State: {section.get('ha_state')}")


register.check_plugin(
    name="prism_ha",
    service_name="NTNX High Availability",
    sections=["prism_ha"],
    discovery_function=discovery_prism_ha,
    check_function=check_prism_ha,
)
