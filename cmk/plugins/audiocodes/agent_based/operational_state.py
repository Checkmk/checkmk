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
    check_audiocodes_operational_state as check_function,
)
from .lib import (
    data_by_item,
    DETECT_AUDIOCODES,
    Module,
    parse_audiocodes_operational_state,
)

snmp_section_audiocodes_operational_state = SimpleSNMPSection(
    name="audiocodes_operational_state",
    detect=DETECT_AUDIOCODES,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5003.9.10.10.4.21.1",
        oids=[
            OIDEnd(),
            "8",  # acSysModuleOperationalState
            "4",  # acSysModulePresence
            "9",  # acSysModuleHAStatus
        ],
    ),
    parse_function=parse_audiocodes_operational_state,
)


def discover_audiocodes_operational_state(
    section_audiocodes_module_names: Mapping[str, str] | None,
    section_audiocodes_operational_state: Mapping[str, Module] | None,
) -> DiscoveryResult:
    if not section_audiocodes_module_names or not section_audiocodes_operational_state:
        return

    yield from (
        Service(item=item)
        for item in data_by_item(
            section_audiocodes_module_names,
            section_audiocodes_operational_state,
        )
    )


def check_audiocodes_operational_state(
    item: str,
    section_audiocodes_module_names: Mapping[str, str] | None,
    section_audiocodes_operational_state: Mapping[str, Module] | None,
) -> CheckResult:
    if not section_audiocodes_operational_state or not section_audiocodes_module_names:
        return

    if (
        module := data_by_item(
            section_audiocodes_module_names,
            section_audiocodes_operational_state,
        ).get(item)
    ) is None:
        return

    yield from check_function(module)


check_plugin_audiocodes_operational_state = CheckPlugin(
    name="audiocodes_operational_state",
    service_name="AudioCodes Operational State Module %s",
    sections=["audiocodes_module_names", "audiocodes_operational_state"],
    discovery_function=discover_audiocodes_operational_state,
    check_function=check_audiocodes_operational_state,
)
