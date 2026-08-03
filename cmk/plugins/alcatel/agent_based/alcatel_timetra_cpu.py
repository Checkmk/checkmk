#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util


@dataclass(frozen=True)
class Section:
    cpu_perc: float


def parse_alcatel_timetra_cpu(string_table: StringTable) -> Section | None:
    return Section(float(string_table[0][0])) if string_table else None


def discover_alcatel_timetra_cpu(section: Section) -> DiscoveryResult:
    yield Service()


def check_alcatel_timetra_cpu(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_cpu_util(
        util=section.cpu_perc,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


snmp_section_alcatel_timetra_cpu = SimpleSNMPSection(
    name="alcatel_timetra_cpu",
    detect=contains(".1.3.6.1.2.1.1.1.0", "TiMOS"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6527.3.1.2.1.1",
        oids=["1"],
    ),
    parse_function=parse_alcatel_timetra_cpu,
)


check_plugin_alcatel_timetra_cpu = CheckPlugin(
    name="alcatel_timetra_cpu",
    service_name="CPU utilization",
    discovery_function=discover_alcatel_timetra_cpu,
    check_function=check_alcatel_timetra_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (90.0, 95.0)},
)
