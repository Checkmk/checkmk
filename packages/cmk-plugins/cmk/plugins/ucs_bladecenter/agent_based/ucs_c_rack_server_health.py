#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# exemplary output of special agent agent_ucs_bladecenter (<TAB> is tabulator):
# storageControllerHealth<TAB>dn
# sys/rack-unit-1/board/storage-SAS-SLOT-HBA/vd-0 <TAB>id SLOT-HBA<TAB>health Good
# storageControllerHealth<TAB>dn
# sys/rack-unit-2/board/storage-SAS-SLOT-HBA/vd-0 <TAB>id SLOT-HBA<TAB>health Good


from collections.abc import Mapping

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

type Section = Mapping[str, str]

# Keys are storage controller health strings provided via special agent -> XML API of servers.
# For information about the data provided by the special agent "storageControllerHealth" refer
# to Cisco C-Series Rack Server XML 2.0 Schema files:
# [https://community.cisco.com/t5/unified-computing-system/cisco-ucs-c-series-standalone-xml-schema/ta-p/3646798]
# Note: The possible string values are not defined/documented in the XML schema.
# "Good" is the only value known from exemplary data output. The data is pre-processed to
# lowercase only chars.
_HEALTH_TO_STATE = {
    "good": State.OK,
}


def parse_ucs_c_rack_server_health(string_table: StringTable) -> Section:
    """
    Input: list of lists containing storage controller health data on a per rack basis.
    Output: Returns dict with indexed Rack Units mapped to keys and lowercase health string
    mapped to value 'health' if rack server has racks attached or empty dict if not.
    """
    parsed = {}
    for _, dn, _id, health in string_table:
        rack_storage_board = (
            dn.replace("dn sys/", "")
            .replace("rack-unit-", "Rack unit ")
            .replace("/board/storage-", " Storage ")
            .replace("-", " ")
            .replace("/", " ")
        )
        parsed[rack_storage_board] = health.replace("health ", "").lower()
    return parsed


def discover_ucs_c_rack_server_health(section: Section) -> DiscoveryResult:
    """
    Yields indexed racks and storage controllers as items
    (e.g. Rack Unit 1 Storage SAS SLOT HBA vd 0).
    """
    yield from (Service(item=item) for item in section)


def check_ucs_c_rack_server_health(item: str, section: Section) -> CheckResult:
    if not (health := section.get(item)):
        return

    if (state := _HEALTH_TO_STATE.get(health)) is None:
        yield Result(state=State.UNKNOWN, summary=f"Status: unknown[{health}]")
    else:
        yield Result(state=state, summary=f"Status: {health}")


agent_section_ucs_c_rack_server_health = AgentSection(
    name="ucs_c_rack_server_health",
    parse_function=parse_ucs_c_rack_server_health,
)


check_plugin_ucs_c_rack_server_health = CheckPlugin(
    name="ucs_c_rack_server_health",
    service_name="Health %s",
    discovery_function=discover_ucs_c_rack_server_health,
    check_function=check_ucs_c_rack_server_health,
)
