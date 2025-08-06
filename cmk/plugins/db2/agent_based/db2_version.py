#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<db2_version>>>
# db2taddm DB2v10.1.0.4,s140509(IP23577)


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


def inventory_db2_version(section: StringTable) -> DiscoveryResult:
    for line in section:
        yield Service(item=line[0].split(" ", 1)[0])


def check_db2_version(item: str, section: StringTable) -> CheckResult:
    for line in section:
        tokens = line[0].split(" ", 1)
        if len(tokens) < 2:
            if item == tokens[0]:
                yield Result(state=State.UNKNOWN, summary="No instance information found")
                return
        else:
            instance, version = tokens
            if item == instance:
                yield Result(state=State.OK, summary=version)
                return

    yield Result(state=State.CRIT, summary="Instance is down")


def parse_db2_version(string_table: StringTable) -> StringTable:
    return string_table


agent_section_db2_version = AgentSection(name="db2_version", parse_function=parse_db2_version)
check_plugin_db2_version = CheckPlugin(
    name="db2_version",
    service_name="DB2 Instance %s",
    discovery_function=inventory_db2_version,
    check_function=check_db2_version,
)
