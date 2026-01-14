#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer untile we migrate the corresponding ruleset.
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
from cmk.plugins.decru.lib import DETECT_DECRU


def parse_decru_fans(string_table: StringTable) -> Mapping[str, int]:
    return {item: int(raw_value) for item, raw_value in string_table}


def discover_decru_fans(section: Mapping[str, int]) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_decru_fans(
    item: str, params: Mapping[str, tuple[int, int]], section: Mapping[str, int]
) -> CheckResult:
    if (rpm := section.get(item)) is None:
        return
    yield from check_levels(
        int(rpm),
        "rpm",
        (None, None) + params["levels_lower"],
        human_readable_func=str,
        infoname="RPM",
    )


snmp_section_decru_fans = SimpleSNMPSection(
    name="decru_fans",
    detect=DETECT_DECRU,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12962.1.2.3.1",
        oids=["2", "3"],
    ),
    parse_function=parse_decru_fans,
)


check_plugin_decru_fans = CheckPlugin(
    name="decru_fans",
    service_name="FAN %s",
    discovery_function=discover_decru_fans,
    check_function=check_decru_fans,
    check_default_parameters={"levels_lower": (8400, 8000)},
)
