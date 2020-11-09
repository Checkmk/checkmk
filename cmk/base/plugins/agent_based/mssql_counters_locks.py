#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Mapping
import time

from .agent_based_api.v1 import (
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
    discovery_mssql_counters_generic,
    get_rate_or_none,
    get_item,
)


def discovery_mssql_counters_locks(section: Section) -> DiscoveryResult:
    """
    >>> for result in discovery_mssql_counters_locks({
    ...     ('MSSQL_VEEAMSQL2012:Locks', '_Total'): {'lock_requests/sec': 3900449701, 'lock_timeouts/sec': 86978, 'number_of_deadlocks/sec': 19, 'lock_waits/sec': 938, 'lock_wait_time_(ms)': 354413},
    ... }):
    ...   print(result)
    Service(item='MSSQL_VEEAMSQL2012:Locks _Total')
    """
    yield from discovery_mssql_counters_generic(
        section,
        {'number_of_deadlocks/sec', 'lock_requests/sec', 'lock_timeouts/sec', 'lock_waits/sec'},
        dflt={},
    )


def _check_common(
    value_store: ValueStore,
    time_point: float,
    node_info: str,
    item: str,
    params: Parameters,
    section: Section,
) -> CheckResult:
    counters, _counter = get_item(item, section)
    now = counters.get("utc_time", time_point)

    for counter_key, title in (
        ('lock_requests/sec', 'Requests'),
        ('lock_timeouts/sec', 'Timeouts'),
        ('number_of_deadlocks/sec', 'Deadlocks'),
        ('lock_waits/sec', 'Waits'),
    ):
        if not counter_key in counters:
            continue

        rate = get_rate_or_none(
            value_store,
            "mssql_counters.locks.%s.%s.%s" % (node_info, item, counter_key),
            now,
            counters[counter_key],
        )

        if rate is None:
            yield IgnoreResults(value="Cannot calculate rates yet")
            continue

        yield from check_levels(
            rate,
            levels_upper=params.get(counter_key),
            render_func=lambda v, i=node_info, t=title: "%s%s: %.1f/s" % (i, t, v),
            metric_name=counter_key.replace("/sec", "_per_second"),
        )


def _check_base(
    value_store: ValueStore,
    time_point: float,
    item: str,
    params: Parameters,
    section: Section,
) -> CheckResult:
    """
    >>> from contextlib import suppress
    >>> vs = {}
    >>> for i in range(2):
    ...     for result in _check_base(vs, 1597839904 + i, "MSSQL_VEEAMSQL2012:Locks _Total lock_requests/sec", {}, {
    ...         ('MSSQL_VEEAMSQL2012:Locks', '_Total'): {'lock_requests/sec': 3900449701 + i, 'lock_timeouts/sec': 86978 + i, 'number_of_deadlocks/sec': 19 + i, 'lock_waits/sec': 938 + i, 'lock_wait_time_(ms)': 354413},
    ...     }):
    ...       print(result)
    Cannot calculate rates yet
    Cannot calculate rates yet
    Cannot calculate rates yet
    Cannot calculate rates yet
    Result(state=<State.OK: 0>, summary='Requests: 1.0/s')
    Metric('lock_requests_per_second', 1.0)
    Result(state=<State.OK: 0>, summary='Timeouts: 1.0/s')
    Metric('lock_timeouts_per_second', 1.0)
    Result(state=<State.OK: 0>, summary='Deadlocks: 1.0/s')
    Metric('number_of_deadlocks_per_second', 1.0)
    Result(state=<State.OK: 0>, summary='Waits: 1.0/s')
    Metric('lock_waits_per_second', 1.0)
    """
    yield from _check_common(value_store, time_point, "", item, params, section)


def check_mssql_counters_locks(
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
    ...   for result in _cluster_check_base(vs, 1597839904 + i, "MSSQL_VEEAMSQL2012:Locks _Total lock_requests/sec", {}, {"node1": {
    ...       ('MSSQL_VEEAMSQL2012:Locks', '_Total'): {'lock_requests/sec': 3900449701 + i, 'lock_timeouts/sec': 86978 + i, 'number_of_deadlocks/sec': 19 + i, 'lock_waits/sec': 938 + i, 'lock_wait_time_(ms)': 354413},
    ...   }}):
    ...     print(result)
    Cannot calculate rates yet
    Cannot calculate rates yet
    Cannot calculate rates yet
    Cannot calculate rates yet
    Result(state=<State.OK: 0>, summary='[node1] Requests: 1.0/s')
    Metric('lock_requests_per_second', 1.0)
    Result(state=<State.OK: 0>, summary='[node1] Timeouts: 1.0/s')
    Metric('lock_timeouts_per_second', 1.0)
    Result(state=<State.OK: 0>, summary='[node1] Deadlocks: 1.0/s')
    Metric('number_of_deadlocks_per_second', 1.0)
    Result(state=<State.OK: 0>, summary='[node1] Waits: 1.0/s')
    Metric('lock_waits_per_second', 1.0)
    """
    for node_name, node_section in section.items():
        yield from _check_common(
            value_store,
            time_point,
            "[%s] " % node_name,
            item,
            params,
            node_section,
        )


def cluster_check_mssql_counters_locks(
    item: str,
    params: Parameters,
    section: Mapping[str, Section],
) -> CheckResult:
    yield from _cluster_check_base(get_value_store(), time.time(), item, params, section)


register.check_plugin(
    name="mssql_counters_locks",
    sections=['mssql_counters'],
    service_name="MSSQL %s Locks",
    discovery_function=discovery_mssql_counters_locks,
    check_default_parameters={},
    check_ruleset_name="mssql_counters_locks",
    check_function=check_mssql_counters_locks,
    cluster_check_function=cluster_check_mssql_counters_locks,
)
