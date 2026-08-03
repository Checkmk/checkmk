#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import json
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

Section = dict[str, Any]

_STATUS_MAP = {
    "OK": (State.OK, "OK"),
    "MAJOR_INCIDENT_CORE": (State.CRIT, "major incident core"),
    "MINOR_INCIDENT_CORE": (State.WARN, "minor incident core"),
    "MAINTENANCE_CORE": (State.OK, "maintenance core"),
    "INFORMATIONAL_CORE": (State.OK, "informational core"),
    "MAJOR_INCIDENT_NONCORE": (State.CRIT, "major incident noncore"),
    "MINOR_INCIDENT_NONCORE": (State.WARN, "minor incident noncore"),
    "MAINTENANCE_NONCORE": (State.OK, "maintenance noncore"),
    "INFORMATIONAL_NONCORE": (State.OK, "informational noncore"),
}


def parse_salesforce(string_table: StringTable) -> Section:
    parsed: Section = {}
    for line in string_table:
        entry = json.loads(" ".join(line))
        if entry.get("key"):
            parsed.setdefault(entry["key"], entry)
    return parsed


def discover_salesforce_instances(section: Section) -> DiscoveryResult:
    for instance, attrs in section.items():
        if attrs.get("isActive"):
            yield Service(item=instance)


def check_salesforce_instances(item: str, section: Section) -> CheckResult:
    if item not in section:
        return
    data = section[item]
    status = data.get("status")
    state, state_readable = _STATUS_MAP.get(status, (State.UNKNOWN, f"unknown[{status}]"))
    yield Result(state=state, summary=f"Status: {state_readable}")
    for key, title in [
        ("environment", "Environment"),
        ("releaseNumber", "Release Number"),
        ("releaseVersion", "Release Version"),
    ]:
        if data.get(key):
            yield Result(state=State.OK, summary=f"{title}: {data[key]}")


agent_section_salesforce_instances = AgentSection(
    name="salesforce_instances",
    parse_function=parse_salesforce,
)
check_plugin_salesforce_instances = CheckPlugin(
    name="salesforce_instances",
    service_name="Salesforce Instance %s",
    discovery_function=discover_salesforce_instances,
    check_function=check_salesforce_instances,
)
