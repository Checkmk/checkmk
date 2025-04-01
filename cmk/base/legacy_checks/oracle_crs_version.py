#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    State,
    StringTable,
)


def inventory_oracle_crs_version(section: StringTable) -> DiscoveryResult:
    for _line in section:
        yield Service()


def check_oracle_crs_version(section: StringTable) -> CheckResult:
    for line in section:
        yield Result(state=State.OK, summary=line[0])
        return

    # In case of missing information we assume that the clusterware
    # is not running and we simple skip the result
    raise IgnoreResultsError("No version details found. Maybe the cssd is not running")


def parse_oracle_crs_version(string_table: StringTable) -> StringTable:
    return string_table


agent_section_oracle_crs_version = AgentSection(
    name="oracle_crs_version",
    parse_function=parse_oracle_crs_version,
)

check_plugin_oracle_crs_version = CheckPlugin(
    name="oracle_crs_version",
    service_name="ORA-GI Version",
    discovery_function=inventory_oracle_crs_version,
    check_function=check_oracle_crs_version,
)
