#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NotRequired, TypedDict

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.sophos.lib import DETECT_SOPHOS


class Params(TypedDict):
    memory_levels: NotRequired[tuple[float, float]]


def parse_sophos_memory(string_table: StringTable) -> int | None:
    try:
        return int(string_table[0][0])
    except ValueError, IndexError:
        return None


def discover_sophos_memory(section: int) -> DiscoveryResult:
    yield Service()


def check_sophos_memory(params: Params, section: int) -> CheckResult:
    yield from check_levels(
        section,
        "memory_util",
        params.get("memory_levels"),
        infoname="Usage",
        human_readable_func=render.percent,
    )


snmp_section_sophos_memory = SimpleSNMPSection(
    name="sophos_memory",
    detect=DETECT_SOPHOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21067.2.1.2.4",
        oids=["2"],
    ),
    parse_function=parse_sophos_memory,
)


check_plugin_sophos_memory = CheckPlugin(
    name="sophos_memory",
    service_name="Memory",
    discovery_function=discover_sophos_memory,
    check_function=check_sophos_memory,
    check_ruleset_name="sophos_memory",
    check_default_parameters=Params(),
)
