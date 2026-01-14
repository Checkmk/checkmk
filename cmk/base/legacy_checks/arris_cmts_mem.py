#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, OIDEnd, SNMPTree
from cmk.base.check_legacy_includes.mem import check_memory_element

check_info = {}


def parse_arris_cmts_mem(string_table):
    parsed = {}
    for cid, heap, heap_free in string_table:
        # The Module numbers are starting with 0, not with 1 like the OIDs
        heap, heap_free = float(heap), float(heap_free)
        parsed.setdefault(
            int(cid) - 1,
            {
                "mem_used": heap - heap_free,
                "mem_total": heap,
            },
        )
    return parsed


def discover_arris_cmts_mem(parsed):
    for k in parsed:
        yield k, {}


def check_arris_cmts_mem(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    levels = params.get("levels")
    yield check_memory_element(
        "Usage",
        data["mem_used"],
        data["mem_total"],
        (
            "abs_used" if isinstance(levels, tuple) and isinstance(levels[0], int) else "perc_used",
            levels,
        ),
        metric_name="mem_used",
    )


check_info["arris_cmts_mem"] = LegacyCheckDefinition(
    name="arris_cmts_mem",
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4998.2.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4998.1.1.5.3.2.1.1",
        oids=[OIDEnd(), "2", "3"],
    ),
    parse_function=parse_arris_cmts_mem,
    service_name="Memory Module %s",
    discovery_function=discover_arris_cmts_mem,
    check_function=check_arris_cmts_mem,
    check_ruleset_name="memory_multiitem",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)
