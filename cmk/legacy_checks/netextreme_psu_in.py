#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState
from cmk.plugins.netextreme.lib import DETECT_NETEXTREME

# .1.3.6.1.4.1.1916.1.1.1.27.1.9.1 52550 --> EXTREME-SYSTEM-MIB::extremePowerSupplyInputPowerUsage.1
# .1.3.6.1.4.1.1916.1.1.1.27.1.9.2 43700 --> EXTREME-SYSTEM-MIB::extremePowerSupplyInputPowerUsage.2
# .1.3.6.1.4.1.1916.1.1.1.27.1.11.1 -3 --> EXTREME-SYSTEM-MIB::extremePowerSupplyInputPowerUsageUnitMultiplier.1
# .1.3.6.1.4.1.1916.1.1.1.27.1.11.2 -3 --> EXTREME-SYSTEM-MIB::extremePowerSupplyInputPowerUsageUnitMultiplier.2

# Just an assumption


def parse_netextreme_psu_in(string_table: StringTable) -> Mapping[str, ElPhase]:
    parsed: dict[str, ElPhase] = {}
    for psu_index, psu_usage_str, psu_factor_str in string_table:
        power = float(psu_usage_str) * pow(10, int(psu_factor_str))
        if power > 0:
            parsed[f"Input {psu_index}"] = ElPhase(
                power=ReadingWithState(value=power),
            )
    return parsed


def discover_netextreme_psu_in(section: Mapping[str, ElPhase]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_netextreme_psu_in(
    item: str, params: Mapping[str, Any], section: Mapping[str, ElPhase]
) -> CheckResult:
    if (elphase := section.get(item)) is None:
        return
    yield from check_elphase(params, elphase)


snmp_section_netextreme_psu_in = SimpleSNMPSection(
    name="netextreme_psu_in",
    detect=DETECT_NETEXTREME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.1.1.27.1",
        oids=[OIDEnd(), "9", "11"],
    ),
    parse_function=parse_netextreme_psu_in,
)


check_plugin_netextreme_psu_in = CheckPlugin(
    name="netextreme_psu_in",
    service_name="Power Supply %s",
    discovery_function=discover_netextreme_psu_in,
    check_function=check_netextreme_psu_in,
    check_ruleset_name="el_inphase",
    check_default_parameters={
        "power": (110, 120),  # This levels a recomended by the manufactorer
    },
)
