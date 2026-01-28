#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.plugins.netextreme.lib import DETECT_NETEXTREME

check_info = {}

# .1.3.6.1.4.1.1916.1.1.1.27.1.9.1 52550 --> EXTREME-SYSTEM-MIB::extremePowerSupplyInputPowerUsage.1
# .1.3.6.1.4.1.1916.1.1.1.27.1.9.2 43700 --> EXTREME-SYSTEM-MIB::extremePowerSupplyInputPowerUsage.2
# .1.3.6.1.4.1.1916.1.1.1.27.1.11.1 -3 --> EXTREME-SYSTEM-MIB::extremePowerSupplyInputPowerUsageUnitMultiplier.1
# .1.3.6.1.4.1.1916.1.1.1.27.1.11.2 -3 --> EXTREME-SYSTEM-MIB::extremePowerSupplyInputPowerUsageUnitMultiplier.2

# Just an assumption


def parse_netextreme_psu_in(string_table: Sequence[Sequence[str]]) -> dict[str, dict[str, float]]:
    parsed: dict[str, dict[str, float]] = {}
    for psu_index, psu_usage_str, psu_factor_str in string_table:
        power = float(psu_usage_str) * pow(10, int(psu_factor_str))
        if power > 0:
            parsed["Input %s" % psu_index] = {
                "power": power,
            }
    return parsed


def discover_netextreme_psu_in(
    section: dict[str, dict[str, float]],
) -> Iterable[tuple[str, dict[str, Any]]]:
    yield from ((item, {}) for item in section)


check_info["netextreme_psu_in"] = LegacyCheckDefinition(
    name="netextreme_psu_in",
    detect=DETECT_NETEXTREME,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1916.1.1.1.27.1",
        oids=[OIDEnd(), "9", "11"],
    ),
    parse_function=parse_netextreme_psu_in,
    service_name="Power Supply %s",
    discovery_function=discover_netextreme_psu_in,
    check_function=check_elphase,
    check_ruleset_name="el_inphase",
    check_default_parameters={
        "power": (110, 120),  # This levels a recomended by the manufactorer
    },
)
