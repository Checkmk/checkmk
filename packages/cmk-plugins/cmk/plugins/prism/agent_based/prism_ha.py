#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Collection, Mapping
from typing import Any, Literal

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
from cmk.plugins.prism.lib import load_json
from cmk.plugins.prism.v4_models import HaHosts

Section = Mapping[str, Any]


def parse_prism_ha(string_table: StringTable) -> Section:
    return load_json(string_table)


agent_section_prism_ha = AgentSection(
    name="prism_ha",
    parse_function=parse_prism_ha,
)

# v4 has no HA object, the cluster's HA state follows from the hypervisor states of its hosts
_HEALING_STATES = frozenset(
    {
        "HA_FAILOVER_SOURCE",
        "HA_FAILOVER_TARGET",
        "HA_HEALING_SOURCE",
        "HA_HEALING_TARGET",
        "ENTERING_MAINTENANCE_MODE_FROM_HA_FAILOVER",
    }
)
_RESERVED_STATES = frozenset({"RESERVED_FOR_HA_FAILOVER"})
_MAINTENANCE_STATES = frozenset({"ENTERING_MAINTENANCE_MODE", "ENTERED_MAINTENANCE_MODE"})
_KNOWN_STATES = (
    _HEALING_STATES
    | _RESERVED_STATES
    | _MAINTENANCE_STATES
    | {
        "ACROPOLIS_NORMAL",
        # The reservation isn't in place yet
        "RESERVING_FOR_HA_FAILOVER",
    }
)


def _ha_state_v2(
    states: Collection[str],
) -> Literal["HighlyAvailable", "Healing", "BestEffort", "Unknown"]:
    if not states:
        # Unlike legacy, the service stays and goes UNKNOWN, so missing host states show
        return "Unknown"
    if any(state in _HEALING_STATES for state in states):
        return "Healing"
    if any(state in _RESERVED_STATES for state in states):
        return "HighlyAvailable"
    return "BestEffort"


def parse_prism_ha_v2(string_table: StringTable) -> Section:
    if not string_table:
        return {}
    hosts = HaHosts.model_validate_json(string_table[0][0]).root
    # Like the legacy agent, HA is only monitored on clusters of AHV hosts
    if not hosts or any(host.hypervisor.hypervisor_type != "AHV" for host in hosts):
        return {}
    states = [
        state
        for host in hosts
        if (state := host.hypervisor.state) is not None and state in _KNOWN_STATES
    ]
    ha_state = _ha_state_v2(states)
    return {
        # v4 can't tell whether HA is enabled
        "failover_enabled": True,
        "ha_state": ha_state,
        "hosts_in_maintenance": sum(state in _MAINTENANCE_STATES for state in states),
        # Segment-based reservation leaves every host in its normal state
        **(
            {"ha_state_note": "HA reservation not visible in v4 API"}
            if ha_state == "BestEffort"
            else {}
        ),
    }


agent_section_prism_ha_v2 = AgentSection(
    name="prism_ha_v2",
    parsed_section_name="prism_ha",
    parse_function=parse_prism_ha_v2,
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

    summary = f"State: {section.get('ha_state')}"
    if note := section.get("ha_state_note"):
        summary += f" ({note})"
    if hosts_in_maintenance := section.get("hosts_in_maintenance", 0):
        hosts = "host" if hosts_in_maintenance == 1 else "hosts"
        summary += f", {hosts_in_maintenance} {hosts} in maintenance mode"

    yield Result(state=State(state), summary=summary)


check_plugin_prism_ha = CheckPlugin(
    name="prism_ha",
    service_name="NTNX High Availability",
    sections=["prism_ha"],
    discovery_function=discovery_prism_ha,
    check_function=check_prism_ha,
)
