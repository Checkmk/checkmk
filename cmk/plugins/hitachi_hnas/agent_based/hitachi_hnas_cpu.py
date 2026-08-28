#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.hitachi_hnas.lib import DETECT
from cmk.plugins.lib.cpu_util import check_cpu_util


def parse_hitachi_hnas_cpu(string_table: StringTable) -> StringTable:
    return string_table


def discover_hitachi_hnas_cpu(section: StringTable) -> DiscoveryResult:
    for id_, _util in section:
        yield Service(item=id_)


def check_hitachi_hnas_cpu(
    item: str, params: Mapping[str, Any], section: StringTable
) -> CheckResult:
    for id_, util in section:
        if id_ == item:
            yield from check_cpu_util(
                util=float(util),
                params=params,
                value_store=get_value_store(),
                this_time=time.time(),
            )
            return

    yield Result(state=State.UNKNOWN, summary="No CPU utilization found")


snmp_section_hitachi_hnas_cpu = SimpleSNMPSection(
    name="hitachi_hnas_cpu",
    parse_function=parse_hitachi_hnas_cpu,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.6.1.2.1",
        oids=["1", "3"],
    ),
)


check_plugin_hitachi_hnas_cpu = CheckPlugin(
    name="hitachi_hnas_cpu",
    service_name="CPU utilization PNode %s",
    discovery_function=discover_hitachi_hnas_cpu,
    check_function=check_hitachi_hnas_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (80.0, 90.0)},
)
