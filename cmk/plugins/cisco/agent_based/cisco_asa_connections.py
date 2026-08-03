#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# .1.3.6.1.4.1.9.9.147.1.2.2.2.1.3.40.6  "number of connections currently in use by the entire firewall"
# .1.3.6.1.4.1.9.9.147.1.2.2.2.1.3.40.7  "highest number of connections in use at any one time since system startup"
# .1.3.6.1.4.1.9.9.147.1.2.2.2.1.5.40.6  1045
# .1.3.6.1.4.1.9.9.147.1.2.2.2.1.5.40.7  2816

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def discover_cisco_asa_connections(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_cisco_asa_connections(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    used_conns = int(section[0][0])
    overall_used_conns = section[1][0]

    yield from check_levels(
        used_conns,
        "fw_connections_active",
        params.get("connections"),
        infoname="Currently used",
    )

    yield Result(state=State.OK, summary=f"Max. since system startup: {overall_used_conns}")


def parse_cisco_asa_connections(string_table: StringTable) -> StringTable | None:
    return string_table or None


snmp_section_cisco_asa_connections = SimpleSNMPSection(
    name="cisco_asa_connections",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.1.0", "cisco adaptive security"),
        startswith(".1.3.6.1.2.1.1.1.0", "cisco firewall services"),
        contains(".1.3.6.1.2.1.1.1.0", "cisco pix security"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.147.1.2.2.2.1",
        oids=["5"],
    ),
    parse_function=parse_cisco_asa_connections,
)


check_plugin_cisco_asa_connections = CheckPlugin(
    name="cisco_asa_connections",
    service_name="Connections",
    discovery_function=discover_cisco_asa_connections,
    check_function=check_cisco_asa_connections,
    check_ruleset_name="cisco_fw_connections",
    check_default_parameters={},
)
