#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# <<<mongodb_instance:sep(9)>>>
# mode secondary
# address 10.1.2.4


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


def inventory_mongodb_instance(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_mongodb_instance(section: StringTable) -> CheckResult:
    for status, messg in section:
        if status == "error":
            yield Result(state=State.CRIT, summary=messg)
        else:
            yield Result(state=State.OK, summary=f"{status.title()}: {messg}")


def parse_mongodb_instance(string_table: StringTable) -> StringTable:
    return string_table


agent_section_mongodb_instance = AgentSection(
    name="mongodb_instance",
    parse_function=parse_mongodb_instance,
)


check_plugin_mongodb_instance = CheckPlugin(
    name="mongodb_instance",
    service_name="MongoDB Instance",
    discovery_function=inventory_mongodb_instance,
    check_function=check_mongodb_instance,
)
