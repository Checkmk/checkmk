#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import List, Mapping

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.utils.casa import DETECT_CASA

Section = Mapping[str, Mapping[str, object]]


def parse_casa_cpu_mem(string_table: List[StringTable]) -> Section:
    entity_names = {int(k): v for k, v in (x for x in string_table[0])}
    data = {}
    for idx, entry in enumerate(string_table[1]):
        entry_nr = int(entry[0])
        data[entity_names[entry_nr]] = {
            "mem_total": int(string_table[1][idx][1]),
            "mem_used": int(string_table[2][idx][1]),
        }
    return data


def inventory_casa_cpu_mem(section: Section) -> Iterable[tuple[str, dict]]:
    for k, v in section.items():
        if v.get("mem_total"):
            yield k, {}


def check_casa_cpu_mem(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    warn, crit = params.get("levels", (None, None))
    mode = "abs_used" if isinstance(warn, int) else "perc_used"
    yield check_memory_element(
        "Usage",
        data["mem_used"],
        data["mem_total"],
        (mode, (warn, crit)),
        metric_name="memused",
    )


check_info["casa_cpu_mem"] = LegacyCheckDefinition(
    detect=DETECT_CASA,
    parse_function=parse_casa_cpu_mem,
    discovery_function=inventory_casa_cpu_mem,
    check_function=check_casa_cpu_mem,
    service_name="Memory %s",
    check_ruleset_name="memory_multiitem",
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
)
