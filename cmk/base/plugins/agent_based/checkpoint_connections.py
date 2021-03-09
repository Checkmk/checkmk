#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    check_levels,
    Metric,
    register,
    Result,
    Service,
    SNMPTree,
    State,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.utils import checkpoint


class Section(NamedTuple):
    current: int
    peak: int
    maximum: int


def parse_checkpoint_connections(string_table: StringTable) -> Section:
    """
    >>> parse_checkpoint_connections([["19190","25230","50000"]])
    Section(current=19190, peak=25230, maximum=50000)
    """
    return Section(
        current=int(string_table[0][0]),
        peak=int(string_table[0][1]),
        maximum=int(string_table[0][2]),
    )


register.snmp_section(
    name="checkpoint_connections",
    parse_function=parse_checkpoint_connections,
    detect=checkpoint.DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2620.1.1.25",
        oids=[
            "3",  # CHECKPOINT-MIB - fwNumConn - current connections
            "4",  # CHECKPOINT-MIB - fwPeakNumConn - peak number of connections
            "10",  # CHECKPOINT-MIB - fwConnTableLimit - connection table limit
        ],
    ),
)


def discover_checkpoint_connections(section: Section) -> DiscoveryResult:
    yield Service()


def check_checkpoint_connections(
    params,
    section: Section,
) -> CheckResult:

    if section.maximum > 0 and "relative_levels" in params:
        warn_pct, crit_pct = params["relative_levels"]
        warn = section.maximum * warn_pct / 100
        crit = section.maximum * crit_pct / 100
        levels_upper = (warn, crit)
    else:
        # use absolute levels if no relative levels provided or no maximum set on CP
        levels_upper = params["levels"]
    yield from check_levels(
        value=section.current,
        levels_upper=levels_upper,
        metric_name="connections",
        label="Current connections",
        render_func=str,
    )

    yield Result(state=State.OK, summary="Peak: {0.peak}".format(section))
    yield Metric(name="peak", value=section.peak, boundaries=(0, None))

    if section.maximum > 0:
        yield Metric(name="connections_pct",
                     value=(section.current * 100.0) / section.maximum,
                     levels=params['relative_levels'],
                     boundaries=(0, 100))
        yield Result(state=State.OK, summary="Connection table limit: {0.maximum}".format(section))


register.check_plugin(
    name="checkpoint_connections",
    service_name="Connections",
    discovery_function=discover_checkpoint_connections,
    check_function=check_checkpoint_connections,
    check_default_parameters={"levels": (40000, 50000)},
    check_ruleset_name="checkpoint_connections",
)
