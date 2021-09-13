#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    register,
    Service,
    SNMPTree,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils import checkpoint


class Section(NamedTuple):
    current: int


def parse_checkpoint_connections(string_table: StringTable) -> Optional[Section]:
    """
    >>> parse_checkpoint_connections([["19190"]])
    Section(current=19190)
    """
    return Section(int(string_table[0][0])) if string_table else None


register.snmp_section(
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
    params,
    section: Section,
) -> CheckResult:
    yield from check_levels(
        value=section.current,
        levels_upper=params["levels"],
        metric_name="connections",
        label="Current connections",
        render_func=str,
    )


register.check_plugin(
    name="checkpoint_connections",
    service_name="Connections",
    discovery_function=discover_checkpoint_connections,
    check_function=check_checkpoint_connections,
    check_default_parameters={"levels": (40000, 50000)},
    check_ruleset_name="checkpoint_connections",
)
