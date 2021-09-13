#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from .agent_based_api.v1 import check_levels, register, render, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.mssql_counters import Counters, Section


def discover_mssql_counters_page_life_expectancy(
    section: Section,
) -> DiscoveryResult:
    """
    >>> list(discover_mssql_counters_page_life_expectancy({
    ...     ('MSSQL_VEEAMSQL2012:Memory_Broker_Clerks', 'Buffer_Pool'): {'memory_broker_clerk_size': 180475, 'simulation_benefit': 0},
    ...     ('MSSQL_VEEAMSQL2012:Buffer_Manager', 'None'): {'buffer_cache_hit_ratio': 3090, 'buffer_cache_hit_ratio_base': 3090, 'page_life_expectancy': 320},
    ... }))
    [Service(item='MSSQL_VEEAMSQL2012:Buffer_Manager page_life_expectancy')]
    """
    yield from (
        Service(
            item=f"{obj} page_life_expectancy"
            if instance == "None"
            else f"{obj} {instance} page_life_expectancy"
        )
        for (obj, instance), counters in section.items()
        if "page_life_expectancy" in counters
    )


def _get_item(item: str, section: Section) -> Counters:
    """
    >>> _get_item('MSSQL_VEEAMSQL2012:Buffer_Manager', {
    ...     ('MSSQL_VEEAMSQL2012:Memory_Broker_Clerks', 'Buffer_Pool'): {'memory_broker_clerk_size': 180475, 'simulation_benefit': 0},
    ...     ('MSSQL_VEEAMSQL2012:Buffer_Manager', 'None'): {'buffer_cache_hit_ratio': 3090, 'buffer_cache_hit_ratio_base': 3090, 'page_life_expectancy': 320},
    ... })
    {'buffer_cache_hit_ratio': 3090, 'buffer_cache_hit_ratio_base': 3090, 'page_life_expectancy': 320}
    """
    sitem = item.split()
    obj = sitem[0]
    if len(sitem) == 3:
        instance = sitem[1]
    else:
        # This is the string set by the plugin if the instance is not defined by MSSQL.
        # We have to keep this for compatibility reasons with other counters. It is stripped
        # off in the discovery of this plugin to return a prettier item name.
        instance = "None"

    return section.get((obj, instance), {})


def check_mssql_counters_page_life_expectancy(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """
    >>> list(check_mssql_counters_page_life_expectancy('MSSQL_VEEAMSQL2012:Buffer_Manager', {'mssql_min_page_life_expectancy': (350, 300)}, {
    ...     ('MSSQL_VEEAMSQL2012:Memory_Broker_Clerks', 'Buffer_Pool'): {'memory_broker_clerk_size': 180475, 'simulation_benefit': 0},
    ...     ('MSSQL_VEEAMSQL2012:Buffer_Manager', 'None'): {'buffer_cache_hit_ratio': 3090, 'buffer_cache_hit_ratio_base': 3090, 'page_life_expectancy': 370},
    ... }))
    [Result(state=<State.OK: 0>, summary='6 minutes 10 seconds'), Metric('page_life_expectancy', 370.0)]
    """
    page_life_expectancy = _get_item(item, section).get("page_life_expectancy")
    if page_life_expectancy is None:
        return

    yield from check_levels(
        page_life_expectancy,
        levels_upper=None,
        levels_lower=params["mssql_min_page_life_expectancy"],
        metric_name="page_life_expectancy",
        render_func=render.timespan,
    )


register.check_plugin(
    name="mssql_counters_page_life_expectancy",
    sections=["mssql_counters"],
    service_name="MSSQL %s",
    discovery_function=discover_mssql_counters_page_life_expectancy,
    check_function=check_mssql_counters_page_life_expectancy,
    check_ruleset_name="mssql_counters_page_life_expectancy",
    check_default_parameters={
        "mssql_min_page_life_expectancy": (350, 300),  # 300 sec is the min defined by Microsoft
    },
)
