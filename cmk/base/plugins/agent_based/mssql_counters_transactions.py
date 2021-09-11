#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Any, Mapping, MutableMapping

from .agent_based_api.v1 import check_levels, get_value_store, IgnoreResults, register
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils.mssql_counters import (
    discovery_mssql_counters_generic,
    get_item,
    get_rate_or_none,
    Section,
)


def discovery_mssql_counters_transactions(section: Section) -> DiscoveryResult:
    """
    >>> for result in discovery_mssql_counters_transactions({
    ...     ('MSSQL_VEEAMSQL2012', 'tempdb'): {'transactions/sec': 24410428, 'tracked_transactions/sec': 0, 'write_transactions/sec': 10381607},
    ... }):
    ...   print(result)
    Service(item='MSSQL_VEEAMSQL2012 tempdb')
    """
    yield from discovery_mssql_counters_generic(
        section, {"transactions/sec", "write_transactions/sec", "tracked_transactions/sec"}
    )


def _check_common(
    value_store: MutableMapping[str, Any],
    time_point: float,
    node_name: str,
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    counters, _counter = get_item(item, section)
    now = counters.get("utc_time", time_point)
    for counter_key, title in (
        ("transactions/sec", "Transactions"),
        ("write_transactions/sec", "Write Transactions"),
        ("tracked_transactions/sec", "Tracked Transactions"),
    ):
        if counter_key not in counters:
            continue

        rate = get_rate_or_none(
            value_store,
            "mssql_counters.transactions.%s.%s.%s" % (node_name, item, counter_key),
            now,
            counters[counter_key],
        )

        if rate is None:
            yield IgnoreResults(value="Cannot calculate rates yet")
            continue

        yield from check_levels(
            rate,
            levels_upper=params.get(counter_key),
            render_func=lambda v, n=node_name, t=title: "%s%s: %.1f/s" % (n and "[%s] " % n, t, v),
            metric_name=counter_key.replace("/sec", "_per_second"),
            boundaries=(0, None),
        )


def _check_base(
    value_store: MutableMapping[str, Any],
    time_point: float,
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """
    >>> vs = {}
    >>> for i in range(2):
    ...   for result in _check_base(vs, 1597839904 + i, "MSSQL_VEEAMSQL2012 tempdb transactions/sec", {}, {
    ...       ('MSSQL_VEEAMSQL2012', 'tempdb'): {'transactions/sec': 24410428 + i, 'tracked_transactions/sec': 0 + i, 'write_transactions/sec': 10381607 + i},
    ...   }):
    ...     print(result)
    Cannot calculate rates yet
    Cannot calculate rates yet
    Cannot calculate rates yet
    Result(state=<State.OK: 0>, summary='Transactions: 1.0/s')
    Metric('transactions_per_second', 1.0, boundaries=(0.0, None))
    Result(state=<State.OK: 0>, summary='Write Transactions: 1.0/s')
    Metric('write_transactions_per_second', 1.0, boundaries=(0.0, None))
    Result(state=<State.OK: 0>, summary='Tracked Transactions: 1.0/s')
    Metric('tracked_transactions_per_second', 1.0, boundaries=(0.0, None))
    """
    yield from _check_common(value_store, time_point, "", item, params, section)


def check_mssql_counters_transactions(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    yield from _check_base(get_value_store(), time.time(), item, params, section)


register.check_plugin(
    name="mssql_counters_transactions",
    sections=["mssql_counters"],
    service_name="MSSQL %s Transactions",
    discovery_function=discovery_mssql_counters_transactions,
    check_default_parameters={},
    check_ruleset_name="mssql_counters_locks",
    check_function=check_mssql_counters_transactions,
)
