#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree, StringTable
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.plugins.casa.lib import DETECT_CASA

check_info = {}

Section = Mapping[str, Mapping[str, object]]


def parse_casa_cpu_mem(string_table: list[StringTable]) -> Section:
    entity_names = {int(k): v for k, v in (x for x in string_table[0])}
    data = {}
    for idx, entry in enumerate(string_table[1]):
        entry_nr = int(entry[0])
        data[entity_names[entry_nr]] = {
            "mem_total": int(string_table[1][idx][1]),
            "mem_used": int(string_table[2][idx][1]),
        }
    return data


def discover_casa_cpu_mem(section: Section) -> Iterable[tuple[str, dict]]:
    for k, v in section.items():
        if v.get("mem_total"):
            yield k, {}


def check_casa_cpu_mem(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    levels = params.get("levels", (None, None))
    yield check_memory_element(
        "Usage",
        data["mem_used"],
        data["mem_total"],
        (
            "abs_used" if isinstance(levels, tuple) and isinstance(levels[0], int) else "perc_used",
            levels,
        ),
        metric_name="memused",
    )


check_info["casa_cpu_mem"] = LegacyCheckDefinition(
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
    service_name="Memory %s",
    discovery_function=discover_casa_cpu_mem,
    check_function=check_casa_cpu_mem,
    check_ruleset_name="memory_multiitem",
    check_default_parameters={"levels": None},
)
