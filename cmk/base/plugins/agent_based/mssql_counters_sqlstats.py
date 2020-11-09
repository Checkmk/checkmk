#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Mapping
import time

from .agent_based_api.v1 import (
    Service,
    IgnoreResults,
    register,
    check_levels,
    get_value_store,
)

from .agent_based_api.v1.type_defs import (
    Parameters,
    CheckResult,
    DiscoveryResult,
    ValueStore,
)

from .utils.mssql_counters import (
    Section,
    get_rate_or_none,
    get_item,
    get_int,
)


def discovery_mssql_counters_sqlstats(section: Section) -> DiscoveryResult:
    """
    >>> for result in discovery_mssql_counters_sqlstats({
    ...     ('MSSQL_VEEAMSQL2012:SQL_Statistics', 'None'): { 'batch_requests/sec': 22476651, 'forced_parameterizations/sec': 0, 'auto-param_attempts/sec': 1133, 'failed_auto-params/sec': 1027, 'safe_auto-params/sec': 8, 'unsafe_auto-params/sec': 98, 'sql_compilations/sec': 2189403, 'sql_re-compilations/sec': 272134, 'sql_attention_rate': 199, 'guided_plan_executions/sec': 0, 'misguided_plan_executions/sec': 0},
    ... }):
    ...   print(result)
    Service(item='MSSQL_VEEAMSQL2012:SQL_Statistics None batch_requests/sec')
    Service(item='MSSQL_VEEAMSQL2012:SQL_Statistics None sql_compilations/sec')
    Service(item='MSSQL_VEEAMSQL2012:SQL_Statistics None sql_re-compilations/sec')
    """
    want_counters = {"batch_requests/sec", "sql_compilations/sec", "sql_re-compilations/sec"}
    yield from (Service(item="%s %s %s" % (obj, instance, counter))
                for (obj, instance), counters in section.items()
                for counter in counters
                if counter in want_counters)


def _check_common(
    value_store: ValueStore,
    time_point: float,
    node_name: str,
    item: str,
    params: Parameters,
    section: Section,
) -> CheckResult:
    counters, counter = get_item(item, section)
    rate = get_rate_or_none(
        value_store,
        "mssql_counters.sqlstats.%s.%s.%s" % (node_name, item, counter),
        counters.get("utc_time", time_point),
        get_int(counters, counter),
    )

    if rate is None:
        yield IgnoreResults(value="Cannot calculate rates yet")
        return

    yield from check_levels(
        rate,
        levels_upper=params.get(counter),
        render_func=lambda v, n=node_name: "%s%.1f/s" % (n and "[%s] " % n, v),
        metric_name=counter.replace("/sec", "_per_second"),
    )


def _check_base(
    value_store: ValueStore,
    time_point: float,
    item: str,
    params: Parameters,
    section: Section,
) -> CheckResult:
    """
    >>> vs = {}
    >>> for i in range(2):
    ...   for result in _check_base(vs, 1597839904 + i, "MSSQL_VEEAMSQL2012:SQL_Statistics None sql_compilations/sec", {}, {
    ...       ('MSSQL_VEEAMSQL2012:SQL_Statistics', 'None'): { 'batch_requests/sec': 22476651, 'forced_parameterizations/sec': 0, 'auto-param_attempts/sec': 1133, 'failed_auto-params/sec': 1027, 'safe_auto-params/sec': 8, 'unsafe_auto-params/sec': 98, 'sql_compilations/sec': 2189403 + i, 'sql_re-compilations/sec': 272134, 'sql_attention_rate': 199, 'guided_plan_executions/sec': 0, 'misguided_plan_executions/sec': 0},
    ...   }):
    ...     print(result)
    Cannot calculate rates yet
    Result(state=<State.OK: 0>, summary='1.0/s')
    Metric('sql_compilations_per_second', 1.0)
    """
    yield from _check_common(value_store, time_point, "", item, params, section)


def check_mssql_counters_sqlstats(
    item: str,
    params: Parameters,
    section: Section,
) -> CheckResult:
    yield from _check_base(get_value_store(), time.time(), item, params, section)


def _cluster_check_base(
    value_store: ValueStore,
    time_point: float,
    item: str,
    params: Parameters,
    section: Mapping[str, Section],
) -> CheckResult:
    """
    >>> vs = {}
    >>> for i in range(2):
    ...   for result in _cluster_check_base(vs, 1597839904 + i, "MSSQL_VEEAMSQL2012:SQL_Statistics None sql_compilations/sec", {}, {"node1": {
    ...       ('MSSQL_VEEAMSQL2012:SQL_Statistics', 'None'): { 'batch_requests/sec': 22476651, 'forced_parameterizations/sec': 0, 'auto-param_attempts/sec': 1133, 'failed_auto-params/sec': 1027, 'safe_auto-params/sec': 8, 'unsafe_auto-params/sec': 98, 'sql_compilations/sec': 2189403 + i, 'sql_re-compilations/sec': 272134, 'sql_attention_rate': 199, 'guided_plan_executions/sec': 0, 'misguided_plan_executions/sec': 0},
    ...   }}):
    ...     print(result)
    Cannot calculate rates yet
    Result(state=<State.OK: 0>, summary='[node1] 1.0/s')
    Metric('sql_compilations_per_second', 1.0)
    """
    for node_name, node_section in section.items():
        yield from _check_common(value_store, time_point, node_name, item, params, node_section)


def cluster_check_mssql_counters_sqlstats(
    item: str,
    params: Parameters,
    section: Mapping[str, Section],
) -> CheckResult:
    yield from _cluster_check_base(get_value_store(), time.time(), item, params, section)


register.check_plugin(
    name="mssql_counters_sqlstats",
    sections=['mssql_counters'],
    service_name="MSSQL %s",  # todo: strange
    discovery_function=discovery_mssql_counters_sqlstats,
    check_default_parameters={},
    check_ruleset_name="mssql_stats",
    check_function=check_mssql_counters_sqlstats,
    cluster_check_function=cluster_check_mssql_counters_sqlstats,
)
