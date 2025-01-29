#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.cisco_ucs import DETECT
from cmk.plugins.lib.temperature import check_temperature
from cmk.plugins.lib.temperature import TempParamType as TempParamType


def parse_cisco_ucs_temp_cpu(string_table: StringTable) -> dict[str, int]:
    return {name.split("/")[3]: int(temp) for name, temp in string_table}


snmp_section_cisco_ucs_temp_cpu = SimpleSNMPSection(
    name="cisco_ucs_temp_cpu",
    parse_function=parse_cisco_ucs_temp_cpu,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.41.2.1",
        oids=[
            "2",  # .1.3.6.1.4.1.9.9.719.1.41.2.1.2  cpu Unit Name
            "10",  # .1.3.6.1.4.1.9.9.719.1.41.2.1.10 cucsProcessorEnvStatsTemperature
        ],
    ),
    detect=DETECT,
)


def discover_cisco_ucs_temp_cpu(section: Mapping[str, int]) -> DiscoveryResult:
    yield from (Service(item=name) for name in section)


def _check_cisco_ucs_temp_cpu(
    item: str,
    params: TempParamType,
    section: Mapping[str, int],
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    if (temperature := section.get(item)) is None:
        return

    yield from check_temperature(
        reading=temperature,
        params=params,
        unique_name=item,
        value_store=value_store,
    )


def check_cisco_ucs_temp_cpu(
    item: str,
    params: TempParamType,
    section: Mapping[str, int],
) -> CheckResult:
    yield from _check_cisco_ucs_temp_cpu(item, params, section, get_value_store())


check_plugin_cisco_ucs_temp_cpu = CheckPlugin(
    name="cisco_ucs_temp_cpu",
    service_name="Temperature CPU %s",
    discovery_function=discover_cisco_ucs_temp_cpu,
    check_function=check_cisco_ucs_temp_cpu,
    check_ruleset_name="temperature",
    check_default_parameters={
        "levels": (75.0, 85.0),
    },
)
