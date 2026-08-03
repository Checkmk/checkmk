#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.casa.lib import DETECT_CASA
from cmk.plugins.lib.memory import check_element

Section = Mapping[str, Mapping[str, int]]


def parse_casa_cpu_mem(string_table: Sequence[StringTable]) -> Section:
    entity_names = {int(k): v for k, v in string_table[0]}
    data: dict[str, Mapping[str, int]] = {}
    for idx, entry in enumerate(string_table[1]):
        entry_nr = int(entry[0])
        data[entity_names[entry_nr]] = {
            "mem_total": int(string_table[1][idx][1]),
            "mem_used": int(string_table[2][idx][1]),
        }
    return data


def discover_casa_cpu_mem(section: Section) -> DiscoveryResult:
    for key, value in section.items():
        if value.get("mem_total"):
            yield Service(item=key)


def check_casa_cpu_mem(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return
    levels = params.get("levels", (None, None))
    yield from check_element(
        "Usage",
        data["mem_used"],
        data["mem_total"],
        (
            "abs_used" if isinstance(levels, tuple) and isinstance(levels[0], int) else "perc_used",
            levels,
        ),
        metric_name="memused",
    )


snmp_section_casa_cpu_mem = SNMPSection(
    name="casa_cpu_mem",
    detect=DETECT_CASA,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.20858.10.13.1.1.1",
            oids=[OIDEnd(), "1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.20858.10.13.1.1.1",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.20858.10.36.1.1.1",
            oids=[OIDEnd(), "1"],
        ),
    ],
    parse_function=parse_casa_cpu_mem,
)
check_plugin_casa_cpu_mem = CheckPlugin(
    name="casa_cpu_mem",
    service_name="Memory %s",
    discovery_function=discover_casa_cpu_mem,
    check_function=check_casa_cpu_mem,
    check_ruleset_name="memory_multiitem",
    check_default_parameters={"levels": None},
)
