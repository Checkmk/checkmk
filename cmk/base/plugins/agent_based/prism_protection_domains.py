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
import time
from typing import Any, Dict, Mapping

from .agent_based_api.v1 import Metric, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.prism import load_json

Section = Dict[str, Mapping[str, Any]]


def parse_prism_protection_domains(string_table: StringTable) -> Section:
    parsed: Section = {}
    data = load_json(string_table)
    for element in data.get("entities", {}):
        parsed.setdefault(element.get("name", "unknown"), element)
    return parsed


register.agent_section(
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


register.check_plugin(
    name="prism_protection_domains",
    service_name="NTNX Data Protection %s",
    sections=["prism_protection_domains"],
    check_default_parameters={},
    discovery_function=discovery_prism_protection_domains,
    check_function=check_prism_protection_domains,
    check_ruleset_name="prism_protection_domains",
)
