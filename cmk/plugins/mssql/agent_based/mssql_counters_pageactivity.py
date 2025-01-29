#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, MutableMapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    GetRateError,
    IgnoreResults,
)
from cmk.plugins.lib.mssql_counters import discovery_mssql_counters_generic, get_item, Section


def discovery_mssql_counters_pageactivity(section: Section) -> DiscoveryResult:
    """
    >>> for result in discovery_mssql_counters_pageactivity({
    ...     ('MSSQL_VEEAMSQL2012:Buffer_Manager', 'None'): { 'page_lookups/sec': 6649047653, 'readahead_pages/sec': 1424319, 'page_reads/sec': 3220650, 'page_writes/sec': 3066377},
    ... }):
    ...   print(result)
    Service(item='MSSQL_VEEAMSQL2012:Buffer_Manager None')
    """
    yield from discovery_mssql_counters_generic(
        section,
        {"page_reads/sec", "page_writes/sec", "page_lookups/sec"},
        dflt={},
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
        p
        for p in (
            ("page_reads/sec", "Reads"),
            ("page_writes/sec", "Writes"),
            ("page_lookups/sec", "Lookups"),
        )
        if p[0] in counters
    ):
        try:
            yield from check_levels_v1(
                value=get_rate(
                    value_store,
                    f"mssql_counters.pageactivity.{node_name or None}.{item}.{counter_key}",
                    now,
                    counters[counter_key],
                ),
                levels_upper=params.get(counter_key),
                render_func=lambda v, n=node_name, t=title: (
                    "{}{}: {:.1f}/s".format(n and "[%s] " % n, t, v)
                ),
                metric_name=counter_key.replace("/sec", "_per_second"),
                boundaries=(0, None),
            )
        except GetRateError:
            yield IgnoreResults("Cannot calculate rates yet")


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
    ...   for result in _check_base(vs, 1597839904 + i, "MSSQL_VEEAMSQL2012:Buffer_Manager None", {}, {
    ...       ('MSSQL_VEEAMSQL2012:Buffer_Manager', 'None'): {'page_lookups/sec': 6649047653 + i, 'readahead_pages/sec': 1424319, 'page_reads/sec': 3220650 + i, 'page_writes/sec': 3066377 + i},
    ...   }):
    ...     print(result)
    Cannot calculate rates yet
    Cannot calculate rates yet
    Cannot calculate rates yet
    Result(state=<State.OK: 0>, summary='Reads: 1.0/s')
    Metric('page_reads_per_second', 1.0, boundaries=(0.0, None))
    Result(state=<State.OK: 0>, summary='Writes: 1.0/s')
    Metric('page_writes_per_second', 1.0, boundaries=(0.0, None))
    Result(state=<State.OK: 0>, summary='Lookups: 1.0/s')
    Metric('page_lookups_per_second', 1.0, boundaries=(0.0, None))
    """
    yield from _check_common(value_store, time_point, "", item, params, section)


def check_mssql_counters_pageactivity(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    yield from _check_base(get_value_store(), time.time(), item, params, section)


check_plugin_mssql_counters_pageactivity = CheckPlugin(
    name="mssql_counters_pageactivity",
    sections=["mssql_counters"],
    service_name="MSSQL %s Page Activity",
    discovery_function=discovery_mssql_counters_pageactivity,
    check_default_parameters={},
    check_ruleset_name="mssql_page_activity",
    check_function=check_mssql_counters_pageactivity,
)
