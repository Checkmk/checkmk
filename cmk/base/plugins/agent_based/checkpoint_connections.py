#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.2.1.1.1.0 Linux gateway1 2.6.18-92cp #1 SMP Tue Dec 4 21:44:22 IST 2012 i686
# .1.3.6.1.4.1.2620.1.1.25.3.0 19190

from typing import NamedTuple

from cmk.base.plugins.agent_based.agent_based_api.v1 import check_levels, register, Result, Service, SNMPTree, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from cmk.base.plugins.agent_based.utils import checkpoint

checkpoint_connections_default_levels = {"pct": (80, 90)}


class Section(NamedTuple):
    current: int
    peak: int
    maximum: int


#def parse_checkpoint_connections(string_table: StringTable) -> Section:
#for whatever reason, this more specific signature fails, I don't understand the error message
def parse_checkpoint_connections(string_table) -> Section:
    current_raw_value = string_table[0][0][0]
    peak_raw_value = string_table[0][0][1]
    maximum_raw_value = string_table[0][0][2]
    return Section(
        current=int(current_raw_value),
        peak=int(peak_raw_value),
        maximum=int(maximum_raw_value),
    )


register.snmp_section(
    name="checkpoint_connections",
    parse_function=parse_checkpoint_connections,
    detect=checkpoint.DETECT,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2620.1.1.25",
            oids=[
                '3',  # CHECKPOINT-MIB - fwNumConn - current connections
                '4',  # CHECKPOINT-MIB - fwPeakNumConn - peak number of connections
                '10',  # CHECKPOINT-MIB - fwConnTableLimit - connection table limit
            ])
    ],
)


def discover_checkpoint_connections(section: Section) -> DiscoveryResult:
    yield Service()


def check_checkpoint_connections(
    params,
    section: Section,
) -> CheckResult:
    maximum = section.maximum
    #infotext = "%d current, %d peak, %d maximum" % (current, peak, maximum)

    if "pct" in params and maximum > 0:
        warn_pct, crit_pct = params["pct"]
        warn = maximum * warn_pct / 100
        crit = maximum * crit_pct / 100
    else:
        # up until cmk 1.6 this check only supported user set absolute values
        warn, crit = params["auto-migration-wrapper-key"]

    upper_boundary = maximum if maximum > 0 else None
    yield from check_levels(
        value=section.current,
        levels_upper=(warn, crit),
        metric_name="connections",
        boundaries=(0, upper_boundary),
        label="Current connections",
    )
    yield Result(state=State.OK,
                 summary="Peak: {0.peak}, Connection table limit: {0.maximum}".format(section))


register.check_plugin(
    name="checkpoint_connections",
    service_name="Connections",
    discovery_function=discover_checkpoint_connections,
    check_function=check_checkpoint_connections,
    check_default_parameters=checkpoint_connections_default_levels,
    check_ruleset_name="checkpoint_connections",
)
