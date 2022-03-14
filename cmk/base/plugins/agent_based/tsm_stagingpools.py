#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Mapping, Optional

from .agent_based_api.v1 import check_levels, Metric, register, Result, Service
from .agent_based_api.v1 import State as state
from .agent_based_api.v1 import type_defs

# <<<tsm_stagingpools>>>
# tsmfarm2       SL8500_STGPOOL_05       99.9
# tsmfarm2       SL8500_STGPOOL_05       97.9
# tsmfarm2       SL8500_LTO4_STGPOOL_01  48.6
# tsmfarm2       SL8500_LTO4_STGPOOL_01  35.9
# tsmfarm2       SL8500_LTO4_STGPOOL_01  58.9
# tsmfarm2       SL8500_LTO4_STGPOOL_01  61.6
#
# Example for params
# params = {
#    "free_below" : 30.0, # consider as free if utilized <= this
#    "levels" : (5, 2), # warn/crit if less then that many free tapes
# }

TSM_STAGINGPOOLS_DEFAULT_LEVELS = {
    "free_below": 70,
}

SECTION = Dict[str, List[str]]


def parse_tsm_stagingpools(string_table: type_defs.StringTable) -> SECTION:
    """
    >>> string_table = [
    ...     ["tsmfarm2", "SL8500_STGPOOL_05", "99.9"],
    ...     ["tsmfarm2", "SL8500_STGPOOL_05", "97.9"],
    ...     ["default", "foo", "7.1"],
    ...     ["default", "foo", "7.4", "default", "foo", "7.2"],
    ... ]
    >>> parse_tsm_stagingpools(string_table)
    {'tsmfarm2 / SL8500_STGPOOL_05': ['99.9', '97.9'], 'foo': ['7.1', '7.4', '7.2']}
    """
    parsed: SECTION = {}

    def add_item(lineinfo):
        inst, pool, util = lineinfo
        if inst == "default":
            item = pool
        else:
            item = inst + " / " + pool
        parsed.setdefault(item, [])
        parsed[item].append(util.replace(",", "."))

    for line in string_table:
        add_item(line[0:3])
        # The agent plugin sometimes seems to mix two lines together some
        # times. Detect and fix that.
        if len(line) == 6:
            add_item(line[3:])

    return parsed


register.agent_section(
    name="tsm_stagingpools",
    parse_function=parse_tsm_stagingpools,
)


def discovery_tsm_stagingpools(section: SECTION) -> type_defs.DiscoveryResult:
    """
    >>> section={'tsmfarm2 / SL8500_STGPOOL_05': ['99.9', '97.9'], 'foo': ['7.1']}
    >>> for service in discovery_tsm_stagingpools(section): print(service)
    Service(item='tsmfarm2 / SL8500_STGPOOL_05')
    Service(item='foo')
    """
    for item in section:
        yield Service(item=item)


def check_tsm_stagingpools(
    item: str,
    params: Mapping[str, Any],
    section: SECTION,
) -> type_defs.CheckResult:
    if item not in section:
        return

    num_tapes = 0
    num_free_tapes = 0
    utilization = 0.0  # in relation to one tape size
    for util in section[item]:
        util_float = float(util) / 100.0
        utilization += util_float
        num_tapes += 1
        if util_float <= params["free_below"] / 100.0:
            num_free_tapes += 1

    if num_tapes == 0:
        yield Result(state=state.UNKNOWN, summary="No tapes in this pool or pool not existant.")
        return

    yield from check_levels(
        num_free_tapes,
        levels_lower=params.get("levels", (None, None)),
        metric_name="free",
        render_func=lambda v: "%d" % v,
        label=(
            f"Total tapes: {num_tapes}, Utilization: {utilization:.1f} tapes, "
            f"Tapes less then {params['free_below']}% full"
        ),
        boundaries=(0, num_tapes),
    )

    for metric_name, value in (("tapes", num_tapes), ("util", utilization)):
        yield Metric(metric_name, value)


def cluster_check_tsm_stagingspools(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Optional[SECTION]],
) -> type_defs.CheckResult:

    datasets, nodeinfos = [], []
    for node, data in section.items():
        if data is not None and item in data:
            datasets.append(tuple(data[item]))
            nodeinfos.append(node)

    if len(datasets) == 0:
        return

    yield Result(state=state.OK, summary="%s: " % "/".join(nodeinfos))

    # In the 1.6 version of this check, a different node may have been checked as in Python 2.7
    # dicts were unordered.
    yield from check_tsm_stagingpools(item, params, {item: list(datasets[0])})

    # In cluster mode we check if data sets are equal from all nodes
    # else we have only one data set
    if len(set(datasets)) > 1:
        yield Result(state=state.UNKNOWN, summary="Cluster: data from nodes are not equal")


register.check_plugin(
    name="tsm_stagingpools",
    service_name="TSM Stagingpool %s",
    discovery_function=discovery_tsm_stagingpools,
    check_function=check_tsm_stagingpools,
    check_default_parameters=TSM_STAGINGPOOLS_DEFAULT_LEVELS,
    check_ruleset_name="tsm_stagingspools",
    cluster_check_function=cluster_check_tsm_stagingspools,
)
