#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDEnd,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.casa.lib import DETECT_CASA
from cmk.plugins.lib.cpu_util import check_cpu_util

Section = Mapping[str, str]


def parse_casa_cpu_util(string_table: Sequence[StringTable]) -> Section:
    entity_names = {int(k): v for k, v in string_table[0]}
    data: dict[str, str] = {}
    for entry in string_table[1]:
        entry_nr = int(entry[0])
        name = entity_names[entry_nr]  # e.g. "Module 1 QEM".
        # Drop "QEM" in order to be consistent with other DTCS checks...
        if name.startswith("Module "):
            name = name.rsplit(None, 1)[0]
        data[name] = entry[1]
    return data


def discover_casa_cpu_util(section: Section) -> DiscoveryResult:
    for key, value in section.items():
        if value:
            yield Service(item=key)


def check_casa_cpu_util(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (value := section.get(item)) is None:
        return
    yield from check_cpu_util(
        util=float(value),
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


snmp_section_casa_cpu_util = SNMPSection(
    name="casa_cpu_util",
    detect=DETECT_CASA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.20858.10.13.1.1.1",
            oids=[OIDEnd(), "4"],
        ),
    ],
    parse_function=parse_casa_cpu_util,
)
check_plugin_casa_cpu_util = CheckPlugin(
    name="casa_cpu_util",
    service_name="CPU utilization %s",
    discovery_function=discover_casa_cpu_util,
    check_function=check_casa_cpu_util,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={},
)
