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
    cpu_levels: NotRequired[tuple[float, float]]


def parse_sophos_cpu(string_table: StringTable) -> int | None:
    try:
        return int(string_table[0][0])
    except ValueError, IndexError:
        return None


def discover_sophos_cpu(section: int) -> DiscoveryResult:
    yield Service()


def check_sophos_cpu(params: Params, section: int) -> CheckResult:
    yield from check_levels(
        section,
        "util",
        params.get("cpu_levels"),
        human_readable_func=render.percent,
        infoname="Total CPU",
        boundaries=(0, 100),
    )


snmp_section_sophos_cpu = SimpleSNMPSection(
    name="sophos_cpu",
    detect=DETECT_SOPHOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21067.2.1.2.2",
        oids=["1"],
    ),
    parse_function=parse_sophos_cpu,
)


check_plugin_sophos_cpu = CheckPlugin(
    name="sophos_cpu",
    service_name="CPU usage",
    discovery_function=discover_sophos_cpu,
    check_function=check_sophos_cpu,
    check_ruleset_name="sophos_cpu",
    check_default_parameters=Params(),
)
