#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

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


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels  # we can only use v2 after migrating the ruleset!
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, str | int]


def parse_mongodb_mem(string_table: StringTable) -> Section:
    parsed: dict[str, str | int] = {}
    for line in string_table:
        key, value = line[0], " ".join(line[1:])
        try:
            parsed[key] = int(value)
        except ValueError:
            parsed[key] = value
    return parsed


def discover_mongodb_mem(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_mongodb_mem(params: Mapping[str, Any], section: Any) -> CheckResult:
    for key in ("resident", "virtual", "mapped"):
        if key in section:  # 'mapped' only for the MMAPv1 storage engine, deprecated with 4x
            value_bytes = section[key] * 1024**2
            yield from check_levels(
                value_bytes,
                metric_name="process_%s_size" % key,
                levels_upper=params.get("%s_levels" % key),
                render_func=render.bytes,
                label="%s usage" % key.title(),
            )

    # MongoDB doc: If virtual value is significantly larger than mapped (e.g. 3 or more times),
    #              this may indicate a memory leak.
    if section.get("mapped"):  # present, non-zero
        virt_mapped_factor = section["virtual"] / float(section["mapped"])
        if virt_mapped_factor >= 3:
            textfmt = "Virtual size is %.1f times the mapped size (possible memory leak)"
            yield Result(state=State.WARN, summary=textfmt % virt_mapped_factor)


agent_section_mongodb_mem = AgentSection(
    name="mongodb_mem",
    parse_function=parse_mongodb_mem,
)


check_plugin_mongodb_mem = CheckPlugin(
    name="mongodb_mem",
    service_name="Memory used MongoDB",
    discovery_function=discover_mongodb_mem,
    check_function=check_mongodb_mem,
    check_ruleset_name="mongodb_mem",
    check_default_parameters={},
)
