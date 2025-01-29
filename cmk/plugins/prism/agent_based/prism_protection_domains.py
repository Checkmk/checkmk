#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.prism import load_json

Section = Mapping[str, Mapping[str, Any]]


def parse_prism_protection_domains(string_table: StringTable) -> Section:
    parsed: dict[str, dict[str, Any]] = {}
    data = load_json(string_table)
    for element in data.get("entities", {}):
        parsed.setdefault(element.get("name", "unknown"), element)
    return parsed


agent_section_prism_protection_domains = AgentSection(
    name="prism_protection_domains",
    parse_function=parse_prism_protection_domains,
)


def discovery_prism_protection_domains(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_prism_protection_domains(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    data = section.get(item)
    if not data:
        return

    mtr = data.get("metro_avail", None)

    _SYNC_STATES = {
        "Enabled": 0,
        "Disabled": 2,
        "Synchronizing": 1,
    }

    if mtr:
        sync_state = mtr.get("status", "Unknown")
        wanted_state = params.get("sync_state", "Enabled")
        summary = (
            f"Type: Metro Availability, "
            f"Role: {mtr.get('role')}, "
            f"Container: {mtr.get('container')}, "
            f"RemoteSite: {mtr.get('remote_site')}, "
        )
        state = 0
        if sync_state != wanted_state:
            state = max(_SYNC_STATES.get(sync_state, 3), _SYNC_STATES.get(wanted_state, 3))
            summary += f"Status: {sync_state} not {wanted_state}(!)"
        else:
            summary += f"Status: {sync_state}"
        yield Result(state=State(state), summary=summary)
    else:
        date = data.get("next_snapshot_time_usecs", None)
        if not date:
            date = "N/A"
        else:
            date = time.strftime("%a %d-%m-%Y %H:%M:%S", time.localtime(float(date)))

        remotes = data.get("remote_site_names", [])
        if not remotes:
            remote = "no remote site defined"
        else:
            remote = ", ".join(remotes)

        exclusivesnapshot = int(data["usage_stats"].get("dr.exclusive_snapshot_usage_bytes"))
        yield Metric("pd_exclusivesnapshot", exclusivesnapshot)
        yield Metric(
            "pd_bandwidthtx", float(data["stats"].get("replication_received_bandwidth_kBps"))
        )
        yield Metric(
            "pd_bandwidthrx", float(data["stats"].get("replication_transmitted_bandwidth_kBps"))
        )
        summary = (
            f"Type: Async DR, "
            f"Exclusive Snapshot Usage: {render.bytes(exclusivesnapshot)}, "
            f"Next Snapshot scheduled at: {date}, "
            f"Total entities: {len(data['vms'])}, "
            f"Remote Site: {remote}"
        )
        yield Result(state=State.OK, summary=summary)


check_plugin_prism_protection_domains = CheckPlugin(
    name="prism_protection_domains",
    service_name="NTNX Data Protection %s",
    sections=["prism_protection_domains"],
    check_default_parameters={},
    discovery_function=discovery_prism_protection_domains,
    check_function=check_prism_protection_domains,
    check_ruleset_name="prism_protection_domains",
)
