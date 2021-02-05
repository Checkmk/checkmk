#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.2.1.1.1.0 Linux gateway1 2.6.18-92cp #1 SMP Tue Dec 4 21:44:22 IST 2012 i686
# .1.3.6.1.4.1.2620.1.1.25.3.0 19190

from typing import NamedTuple

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    register,
    Service,
    SNMPTree,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.utils import checkpoint

checkpoint_connections_default_levels = {"levels": (40000, 50000)}


class Section(NamedTuple):
    current: int


def parse_checkpoint_connections(string_table) -> Section:
    current_raw_value = string_table[0][0][0]
    return Section(current=int(current_raw_value),)


register.snmp_section(
    name="checkpoint_connections",
    parse_function=parse_checkpoint_connections,
    detect=checkpoint.DETECT,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2620.1.1.25",
            oids=[
                '3',  # CHECKPOINT-MIB - fwNumConn - current connections
            ])
    ],
)


def discover_checkpoint_connections(section: Section) -> DiscoveryResult:
    yield Service()


def check_checkpoint_connections(
    params,
    section: Section,
) -> CheckResult:

    if 'levels' in params:
        levels_upper = params["levels"]
    else:
        # get auto wrapped params from pre 2.0 configs
        levels_upper = params["auto-migration-wrapper-key"]

    yield from check_levels(
        value=section.current,
        levels_upper=levels_upper,
        metric_name="connections",
        label="Current connections",
    )


register.check_plugin(
    name="checkpoint_connections",
    service_name="Connections",
    discovery_function=discover_checkpoint_connections,
    check_function=check_checkpoint_connections,
    check_default_parameters=checkpoint_connections_default_levels,
    check_ruleset_name="checkpoint_connections",
)
