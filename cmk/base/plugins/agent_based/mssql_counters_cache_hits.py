#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from .agent_based_api.v1 import check_levels, register, render, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.mssql_counters import get_int, get_item, Section


def discovery_mssql_counters_cache_hits(
    params: Mapping[str, Any],
    section: Section,
) -> DiscoveryResult:
    """
    >>> for result in discovery_mssql_counters_cache_hits({}, {
    ...     ('MSSQL_VEEAMSQL2012:Memory_Broker_Clerks', 'Buffer_Pool'): {'memory_broker_clerk_size': 180475, 'simulation_benefit': 0},
    ...     ('MSSQL_VEEAMSQL2012:Buffer_Manager', 'None'): {'buffer_cache_hit_ratio': 3090, 'buffer_cache_hit_ratio_base': 3090},
    ...     ('MSSQL_VEEAMSQL2012:Plan_Cache', 'Temporary_Tables_&_Table_Variables'): {'cache_hit_ratio': 588},
    ...     ('MSSQL_VEEAMSQL2012:Cursor_Manager_by_Type', 'TSQL_Local_Cursor'): {'cache_hit_ratio': 730},
    ...     ('MSSQL_VEEAMSQL2012:Catalog_Metadata', 'tempdb'): {'cache_hit_ratio': 29305065, 'cache_hit_ratio_base': 29450560},
    ... }):
    ...   print(result)
    Service(item='MSSQL_VEEAMSQL2012:Buffer_Manager None buffer_cache_hit_ratio')
    Service(item='MSSQL_VEEAMSQL2012:Catalog_Metadata tempdb cache_hit_ratio')
    """
    want_counters = {"cache_hit_ratio", "log_cache_hit_ratio", "buffer_cache_hit_ratio"}
    yield from (
        Service(item="%s %s %s" % (obj, instance, counter))
        for (obj, instance), counters in section.items()
        for counter in counters
        if counter in want_counters
        if (counters.get("%s_base" % counter, 0.0) != 0.0 or params.get("add_zero_based_services"))
    )


def _check_common(
    node_name: str,
    item: str,
    section: Section,
) -> CheckResult:
    counters, counter = get_item(item, section)
    value = get_int(counters, counter)
    base = get_int(counters, "%s_base" % counter)
    yield from check_levels(
        (100 * value / base) if base != 0 else 0,
        render_func=lambda v: "%s%s" % (node_name and "[%s] " % node_name, render.percent(v)),
        metric_name=counter,
    )


def check_mssql_counters_cache_hits(
    item: str,
    section: Section,
) -> CheckResult:
    """
    >>> for result in check_mssql_counters_cache_hits(
    ...   "MSSQL_VEEAMSQL2012:Catalog_Metadata mssqlsystemresource cache_hit_ratio", {
    ...     ('None', 'None'): {'utc_time': 1597839904.0},
    ...     ('MSSQL_VEEAMSQL2012:SQL_Statistics', 'None'): {'batch_requests/sec': 22476651, 'forced_parameterizations/sec': 0, 'auto-param_attempts/sec': 1133, 'failed_auto-params/sec': 1027, 'safe_auto-params/sec': 8, 'unsafe_auto-params/sec': 98, 'sql_compilations/sec': 2189403, 'sql_re-compilations/sec': 272134, 'sql_attention_rate': 199, 'guided_plan_executions/sec': 0, 'misguided_plan_executions/sec': 0},
    ...     ('MSSQL_VEEAMSQL2012:Catalog_Metadata', 'mssqlsystemresource'): {'cache_hit_ratio': 77478, 'cache_hit_ratio_base': 77796, 'cache_entries_count': 73, 'cache_entries_pinned_count': 0},
    ... }):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='99.59%')
    Metric('cache_hit_ratio', 99.59123862409379)
    """
    yield from _check_common("", item, section)


register.check_plugin(
    name="mssql_counters_cache_hits",
    sections=["mssql_counters"],
    service_name="MSSQL %s",
    discovery_function=discovery_mssql_counters_cache_hits,
    discovery_ruleset_name="inventory_mssql_counters_rules",
    discovery_default_parameters={},
    check_function=check_mssql_counters_cache_hits,
)
