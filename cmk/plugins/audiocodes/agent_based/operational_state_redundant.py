#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
)

from .lib import (
    check_audiocodes_operational_state,
    DETECT_AUDIOCODES,
    Module,
    parse_audiocodes_operational_state,
)

snmp_section_audiocodes_operational_state_redundant = SimpleSNMPSection(
    name="audiocodes_operational_state_redundant",
    detect=DETECT_AUDIOCODES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5003.9.10.10.4.27.21.1",
        oids=[
            OIDEnd(),
            "8",  # acSysModuleOperationalState
            "4",  # acSysModulePresence
            "9",  # acSysModuleHAStatus
        ],
    ),
    parse_function=parse_audiocodes_operational_state,
)


def discover_audiocodes_operational_state_redundant(
    section: Mapping[str, Module],
) -> DiscoveryResult:
    yield from (Service(item=redundant_module) for redundant_module in section)


def check_audiocodes_operational_state_redundant(
    item: str,
    section: Mapping[str, Module],
) -> CheckResult:
    if (redundant_module := section.get(item)) is None:
        return

    yield from check_audiocodes_operational_state(redundant_module)


check_plugin_audiocodes_operational_state_redundant = CheckPlugin(
    name="audiocodes_operational_state_redundant",
    service_name="Operational State Redundant Module %s",
    discovery_function=discover_audiocodes_operational_state_redundant,
    check_function=check_audiocodes_operational_state_redundant,
)
