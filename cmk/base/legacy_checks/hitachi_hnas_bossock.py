#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.hitachi_hnas import DETECT

DiscoveryResult = Iterable[tuple[str, Mapping]]
CheckResult = Iterable[tuple[int, str, list]]
Section = Mapping[str, int]


def parse_hitachi_hnas_bossock(string_table: StringTable) -> Section:
    return {clusternode: int(fibers) for clusternode, fibers in string_table}


def discover_hitachi_hnas_bossock(section: Section) -> DiscoveryResult:
    for clusternode in section:
        yield clusternode, {}


def check_hitachi_hnas_bossock(
    item: str, params: Mapping[str, tuple[int, int]], section: Section
) -> CheckResult:
    if (fibers := section.get(item)) is None:
        return

    yield check_levels(
        fibers, "fibers", params["levels"], human_readable_func=str, infoname="Running"
    )


check_info["hitachi_hnas_bossock"] = LegacyCheckDefinition(
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.6.7.4.1",
        oids=["1", "2"],
    ),
    service_name="Bossock Fibers on Node %s",
    parse_function=parse_hitachi_hnas_bossock,
    discovery_function=discover_hitachi_hnas_bossock,
    check_function=check_hitachi_hnas_bossock,
    check_ruleset_name="bossock_fibers",
    check_default_parameters={"levels": (250, 350)},
)
