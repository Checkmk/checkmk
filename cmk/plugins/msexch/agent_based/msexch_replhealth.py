#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example Output:
# <<<msexch_replhealth:sep(58)>>>
# RunspaceId       : d58353f4-f868-43b2-8404-25875841a47b
# Server           : S0141KL
# Check            : ClusterService
# CheckDescription : Überprüft, ob der Status des lokalen Clusterdiensts einwandfrei ist.
# Result           : Prüfung bestanden
# Error            :
# Identity         :
# IsValid          : True
#
# RunspaceId       : d58353f4-f868-43b2-8404-25875841a47b
# Server           : S0141KL
# Check            : ReplayService
# CheckDescription : Überprüft, ob der Microsoft Exchange-Replikationsdienst ausgeführt wird.
# Result           : Prüfung bestanden
# Error            :
# Identity         :
# IsValid          : True
#

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


def parse_msexch_replhealth(string_table: StringTable) -> StringTable:
    return string_table


def discover_msexch_replhealth(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[0].strip().lower() == "check":
            yield Service(item=line[1].strip())


def check_msexch_replhealth(item: str, section: StringTable) -> CheckResult:
    getit = False
    for line in section:
        if len(line) == 2:
            key, val = (i.strip() for i in line)
            if key == "Check" and val == item:
                getit = True
            elif key == "Result" and getit:
                if val == "Passed" or val.endswith("fung bestanden"):
                    yield Result(state=State.OK, summary="Test Passed")
                else:
                    yield Result(state=State.WARN, summary=val)
                return


agent_section_msexch_replhealth = AgentSection(
    name="msexch_replhealth",
    parse_function=parse_msexch_replhealth,
)


check_plugin_msexch_replhealth = CheckPlugin(
    name="msexch_replhealth",
    service_name="Exchange Replication Health %s",
    discovery_function=discover_msexch_replhealth,
    check_function=check_msexch_replhealth,
)
