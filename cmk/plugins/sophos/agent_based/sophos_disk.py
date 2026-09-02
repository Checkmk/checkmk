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
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.sophos.lib import DETECT_SOPHOS


class Params(TypedDict):
    disk_levels: NotRequired[tuple[float, float]]


def parse_sophos_disk(string_table: StringTable) -> int | None:
    try:
        return int(string_table[0][0])
    except ValueError, IndexError:
        return None


def discover_sophos_disk(section: int) -> DiscoveryResult:
    yield Service()


def check_sophos_disk(params: Params, section: int) -> CheckResult:
    yield from check_levels(
        section,
        "disk_utilization",
        params.get("disk_levels"),
        human_readable_func=lambda x: f"{int(x)}%",
        infoname="Disk percentage usage",
    )


snmp_section_sophos_disk = SimpleSNMPSection(
    name="sophos_disk",
    detect=DETECT_SOPHOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21067.2.1.2.3",
        oids=["2"],
    ),
    parse_function=parse_sophos_disk,
)


check_plugin_sophos_disk = CheckPlugin(
    name="sophos_disk",
    service_name="Disk usage",
    discovery_function=discover_sophos_disk,
    check_function=check_sophos_disk,
    check_ruleset_name="sophos_disk",
    check_default_parameters=Params(),
)
