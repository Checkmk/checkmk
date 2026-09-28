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
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState
from cmk.plugins.netextreme.lib import DETECT_NETEXTREME

# .1.3.6.1.4.1.1916.1.1.1.40.1.0 96250 --> EXTREME-SYSTEM-MIB::extremeSystemPowerUsageValue.0
# .1.3.6.1.4.1.1916.1.1.1.40.2.0 -3 --> EXTREME-SYSTEM-MIB::extremeSystemPowerUsageUnitMultiplier.0

# Maximum power consumption is 123 W
# as in the documentation 'Summit-X460-G2-DS.pdf'


def parse_netextreme_psu(string_table: StringTable) -> Mapping[str, ElPhase]:
    try:
        return {
            "1": ElPhase(
                power=ReadingWithState(
                    value=float(string_table[0][0]) * pow(10, int(string_table[0][1]))
                )
            )
        }
    except IndexError, ValueError:
        return {}


def discover_netextreme_psu(section: Mapping[str, ElPhase]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_netextreme_psu(
    item: str, params: Mapping[str, Any], section: Mapping[str, ElPhase]
) -> CheckResult:
    if (elphase := section.get(item)) is None:
        return
    yield from check_elphase(params, elphase)


snmp_section_netextreme_psu = SimpleSNMPSection(
    name="netextreme_psu",
    detect=DETECT_NETEXTREME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.1.1.40",
        oids=["1", "2"],
    ),
    parse_function=parse_netextreme_psu,
)


check_plugin_netextreme_psu = CheckPlugin(
    name="netextreme_psu",
    service_name="Power Supply %s",
    discovery_function=discover_netextreme_psu,
    check_function=check_netextreme_psu,
    check_ruleset_name="el_inphase",
    check_default_parameters={
        "power": (110, 120),
    },
)
