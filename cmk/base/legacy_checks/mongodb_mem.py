#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<mongodb_mem>>>
# resident 856
# supported True
# virtual 6100
# mappedWithJournal 5374
# mapped 2687
# bits 64
# note fields vary by platform
# page_faults 86
# heap_usage_bytes 65501032


from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render

check_info = {}

Section = Mapping[str, str | int]


def parse_mongodb_mem(string_table):
    parsed: dict[str, str | int] = {}
    for line in string_table:
        key, value = line[0], " ".join(line[1:])
        try:
            parsed[key] = int(value)
        except ValueError:
            parsed[key] = value
    return parsed


def discover_mongodb_mem(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_mongodb_mem(_no_item, params, parsed):
    for key in ("resident", "virtual", "mapped"):
        if key in parsed:  # 'mapped' only for the MMAPv1 storage engine, deprecated with 4x
            value_bytes = parsed[key] * 1024**2
            levels = params.get("%s_levels" % key, (None, None))
            yield check_levels(
                value_bytes,
                "process_%s_size" % key,
                levels,
                human_readable_func=render.bytes,
                infoname="%s usage" % key.title(),
            )

    # MongoDB doc: If virtual value is significantly larger than mapped (e.g. 3 or more times),
    #              this may indicate a memory leak.
    if parsed.get("mapped"):  # present, non-zero
        virt_mapped_factor = parsed["virtual"] / float(parsed["mapped"])
        if virt_mapped_factor >= 3:
            textfmt = "Virtual size is %.1f times the mapped size (possible memory leak)"
            yield 1, textfmt % virt_mapped_factor


check_info["mongodb_mem"] = LegacyCheckDefinition(
    name="mongodb_mem",
    parse_function=parse_mongodb_mem,
    service_name="Memory used MongoDB",
    discovery_function=discover_mongodb_mem,
    check_function=check_mongodb_mem,
    check_ruleset_name="mongodb_mem",
)
