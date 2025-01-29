#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import (
    check_levels as check_levels_v1,  # we can only use v2 after migrating the ruleset!
)
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
)
from cmk.plugins.liebert.agent_based.lib import DETECT_LIEBERT, parse_liebert_float, Section


def check_liebert_compressor(
    item: str, params: Mapping[str, Any], section: Section[float]
) -> CheckResult:
    try:
        value, unit = section[item]
    except KeyError:
        return
    yield from check_levels_v1(
        value,
        metric_name=None,
        levels_upper=params["levels"],
        label="Head pressure",
        render_func=lambda x: f"{x:.2f} {unit}",
    )


def discover_liebert_compressor(section: Section[float]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_liebert_compressor = SimpleSNMPSection(
    name="liebert_compressor",
    detect=DETECT_LIEBERT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=["10.1.2.1.5266", "20.1.2.1.5266", "30.1.2.1.5266"],
    ),
    parse_function=parse_liebert_float,
)
check_plugin_liebert_compressor = CheckPlugin(
    name="liebert_compressor",
    service_name="%s",
    discovery_function=discover_liebert_compressor,
    check_function=check_liebert_compressor,
    check_default_parameters={
        "levels": (8, 12),
    },
)
