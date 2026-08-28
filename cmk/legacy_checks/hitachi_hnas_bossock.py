#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.hitachi_hnas.lib import DETECT

Section = Mapping[str, int]


def parse_hitachi_hnas_bossock(string_table: StringTable) -> Section:
    return {clusternode: int(fibers) for clusternode, fibers in string_table}


def discover_hitachi_hnas_bossock(section: Section) -> DiscoveryResult:
    for clusternode in section:
        yield Service(item=clusternode)


def check_hitachi_hnas_bossock(
    item: str, params: Mapping[str, tuple[int, int] | None], section: Section
) -> CheckResult:
    if (fibers := section.get(item)) is None:
        return

    yield from check_levels(
        fibers,
        metric_name="fibers",
        levels_upper=("fixed", levels) if (levels := params["levels"]) else ("no_levels", None),
        render_func=str,
        label="Running",
    )


snmp_section_hitachi_hnas_bossock = SimpleSNMPSection(
    name="hitachi_hnas_bossock",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.6.7.4.1",
        oids=["1", "2"],
    ),
    parse_function=parse_hitachi_hnas_bossock,
)


check_plugin_hitachi_hnas_bossock = CheckPlugin(
    name="hitachi_hnas_bossock",
    service_name="Bossock Fibers on Node %s",
    discovery_function=discover_hitachi_hnas_bossock,
    check_function=check_hitachi_hnas_bossock,
    check_ruleset_name="bossock_fibers",
    check_default_parameters={"levels": (250, 350)},
)
