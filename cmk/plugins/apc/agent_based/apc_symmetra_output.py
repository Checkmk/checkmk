#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from cmk.plugins.apc.lib_ats import DETECT
from cmk.plugins.lib.elphase import check_elphase, ElPhase, ReadingWithState

# .1.3.6.1.4.1.318.1.1.1.4.2.1.0 231
# .1.3.6.1.4.1.318.1.1.1.4.2.4.0
# .1.3.6.1.4.1.318.1.1.1.4.2.3.0 37

type Section = Mapping[str, ElPhase]


def parse_apc_symmetra_output(string_table: StringTable) -> Section:
    if not string_table:
        return {}

    kwargs: dict[str, ReadingWithState] = {}
    for key, value_str in zip(["voltage", "current", "output_load"], string_table[0]):
        try:
            value = float(value_str)
        except ValueError:
            continue
        kwargs[key] = ReadingWithState(value=value)

    if not kwargs:
        return {}
    return {"Output": ElPhase.from_dict(kwargs)}


def discover_apc_symmetra_output(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_apc_symmetra_output(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    yield from check_elphase(params, data)


snmp_section_apc_symmetra_output = SimpleSNMPSection(
    name="apc_symmetra_output",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.1.4.2",
        oids=["1", "4", "3"],
    ),
    parse_function=parse_apc_symmetra_output,
)


check_plugin_apc_symmetra_output = CheckPlugin(
    name="apc_symmetra_output",
    service_name="Phase %s",
    discovery_function=discover_apc_symmetra_output,
    check_function=check_apc_symmetra_output,
    check_ruleset_name="ups_outphase",
    check_default_parameters={
        "voltage": (220, 220),
    },
)
