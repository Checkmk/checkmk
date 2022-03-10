#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Mapping, MutableMapping

from .agent_based_api.v1 import (
    check_levels,
    get_value_store,
    IgnoreResults,
    IgnoreResultsError,
    register,
    Service,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.mssql_counters import get_int, get_rate_or_none, Section


def discovery_mssql_counters_locks_per_batch(section: Section) -> DiscoveryResult:
    """
    >>> for result in discovery_mssql_counters_locks_per_batch({
    ...     ('MSSQL_VEEAMSQL2012:Batch_Resp_Statistics', 'CPU_Time:Total(ms)'): { 'batches_>=000000ms_&_<000001ms': 0, 'batches_>=000001ms_&_<000002ms': 668805},
    ...     ('MSSQL_VEEAMSQL2012:SQL_Statistics', 'None'): { 'batch_requests/sec': 22476651, 'forced_parameterizations/sec': 0, 'auto-param_attempts/sec': 1133, 'failed_auto-params/sec': 1027, 'safe_auto-params/sec': 8, 'unsafe_auto-params/sec': 98, 'sql_compilations/sec': 2189403, 'sql_re-compilations/sec': 272134, 'sql_attention_rate': 199, 'guided_plan_executions/sec': 0, 'misguided_plan_executions/sec': 0},
    ...     ('MSSQL_VEEAMSQL2012:Locks', '_Total'): { 'lock_requests/sec': 3900449701, 'lock_timeouts/sec': 86978, 'number_of_deadlocks/sec': 19, 'lock_waits/sec': 938, 'lock_wait_time_(ms)': 354413, 'average_wait_time_(ms)': 354413, 'average_wait_time_base': 938, 'lock_timeouts_(timeout_>_0)/sec': 0},
    ... }):
    ...   print(result)
    Service(item='MSSQL_VEEAMSQL2012')
    """
    db_names = (
        db_name  #
        for (obj, instance), counters in section.items()
        if ":" in obj
        for db_name in (obj.split(":")[0],)
    )

    yield from (
        Service(item=item_name)
        for item_name in set(  #
            db_name
            for db_name in db_names
            if "lock_requests/sec" in section.get(("%s:Locks" % db_name, "_Total"), {})
            if "batch_requests/sec" in section.get(("%s:SQL_Statistics" % db_name, "None"), {})
        )
    )


def _check_common(
    value_store: MutableMapping[str, Any],
    node_name: str,
    item: str,
    params: Mapping[str, Any],
    section: Section,
    live_now: float,
) -> CheckResult:
    data_locks = section.get(("%s:Locks" % item, "_Total"), {})
    data_stats = section.get(("%s:SQL_Statistics" % item, "None"), {})

    if not data_locks and not data_stats:
        raise IgnoreResultsError("Item not found in monitoring data")

    now = data_locks.get("utc_time", data_stats.get("utc_time")) or live_now
    lock_rate_base = get_int(data_locks, "lock_requests/sec")
    batch_rate_base = get_int(data_stats, "batch_requests/sec")

    lock_rate = get_rate_or_none(
        value_store,
        "mssql_counters_locks_per_batch.%s.%s.locks" % (node_name, item),
        now,
        lock_rate_base,
    )
    batch_rate = get_rate_or_none(
        value_store,
        "mssql_counters_locks_per_batch.%s.%s.batches" % (node_name, item),
        now,
        batch_rate_base,
    )
    if lock_rate is None or batch_rate is None:
        yield IgnoreResults("Cannot calculate rates yet")
        return

    yield from check_levels(
        lock_rate / batch_rate if batch_rate else 0,
        levels_upper=params.get("locks_per_batch"),
        metric_name="locks_per_batch",
        render_func=lambda v: "%s%.1f" % (node_name and "[%s] " % node_name, v),
        boundaries=(0, None),
    )


def _check_base(
    value_store: MutableMapping[str, Any],
    item: str,
    params: Mapping[str, Any],
    section: Section,
    live_now: float,
) -> CheckResult:
    """
    >>> from contextlib import suppress
    >>> vs = {}
    >>> for i in range(2):
    ...   with suppress(IgnoreResultsError):
    ...     for result in _check_base(vs, "MSSQL_VEEAMSQL2012", {}, {
    ...         ('MSSQL_VEEAMSQL2012:SQL_Statistics', 'None'): {'batch_requests/sec': 22476651+i, 'forced_parameterizations/sec': 0, 'auto-param_attempts/sec': 1133, 'failed_auto-params/sec': 1027, 'safe_auto-params/sec': 8, 'unsafe_auto-params/sec': 98, 'sql_compilations/sec': 2189403, 'sql_re-compilations/sec': 272134, 'sql_attention_rate': 199, 'guided_plan_executions/sec': 0, 'misguided_plan_executions/sec': 0},
    ...         ('MSSQL_VEEAMSQL2012:Locks', '_Total'): {'lock_requests/sec': 3900449701+i, 'lock_timeouts/sec': 86978, 'number_of_deadlocks/sec': 19, 'lock_waits/sec': 938, 'lock_wait_time_(ms)': 354413, 'average_wait_time_(ms)': 354413, 'average_wait_time_base': 938, 'lock_timeouts_(timeout_>_0)/sec': 0},
    ...     }, i*60.0):
    ...       print(result)
    Cannot calculate rates yet
    Result(state=<State.OK: 0>, summary='1.0')
    Metric('locks_per_batch', 1.0, boundaries=(0.0, None))
    """
    yield from _check_common(value_store, "", item, params, section, live_now)


def check_mssql_counters_locks_per_batch(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    yield from _check_base(get_value_store(), item, params, section, time.time())


register.check_plugin(
    name="mssql_counters_locks_per_batch",
    sections=["mssql_counters"],
    service_name="MSSQL %s Locks per Batch",
    discovery_function=discovery_mssql_counters_locks_per_batch,
    check_default_parameters={},
    check_ruleset_name="mssql_stats",
    check_function=check_mssql_counters_locks_per_batch,
)
