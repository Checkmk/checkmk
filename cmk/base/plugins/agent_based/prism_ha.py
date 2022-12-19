#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
# This is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
from typing import Any, Dict, Mapping

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.prism import load_json

Section = Dict[str, Mapping[str, Any]]


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
