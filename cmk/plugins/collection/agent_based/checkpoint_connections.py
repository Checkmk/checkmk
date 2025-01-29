#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib import checkpoint


class Section(NamedTuple):
    current: int


def parse_checkpoint_connections(string_table: StringTable) -> Section | None:
    """
    >>> parse_checkpoint_connections([["19190"]])
    Section(current=19190)
    """
    return Section(int(string_table[0][0])) if string_table else None


snmp_section_checkpoint_connections = SimpleSNMPSection(
    name="checkpoint_connections",
    parse_function=parse_checkpoint_connections,
    detect=checkpoint.DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.1.25",
        oids=[
            "3",  # CHECKPOINT-MIB - fwNumConn - current connections
        ],
    ),
)


def discover_checkpoint_connections(section: Section) -> DiscoveryResult:
    yield Service()


def check_checkpoint_connections(
    params: dict[str, Any],
    section: Section,
) -> CheckResult:
    yield from check_levels_v1(
        value=section.current,
        levels_upper=params["levels"],
        metric_name="connections",
        label="Current connections",
        render_func=str,
    )


check_plugin_checkpoint_connections = CheckPlugin(
    name="checkpoint_connections",
    service_name="Connections",
    discovery_function=discover_checkpoint_connections,
    check_function=check_checkpoint_connections,
    check_default_parameters={"levels": (40000, 50000)},
    check_ruleset_name="checkpoint_connections",
)
