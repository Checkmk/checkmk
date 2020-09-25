#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping
import time

from .agent_based_api.v1 import (
    IgnoreResults,
    GetRateError,
    register,
    check_levels,
    get_value_store,
    get_rate,
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
    get_item,
)


def discovery_mssql_counters_pageactivity(section: Section) -> DiscoveryResult:
    """
    >>> for result in discovery_mssql_counters_pageactivity({
    ...     ('MSSQL_VEEAMSQL2012:Buffer_Manager', 'None'): { 'page_lookups/sec': 6649047653, 'readahead_pages/sec': 1424319, 'page_reads/sec': 3220650, 'page_writes/sec': 3066377},
    ... }):
    ...   print(result)
    Service(item='MSSQL_VEEAMSQL2012:Buffer_Manager None page_lookups/sec', parameters={}, labels=[])
    Service(item='MSSQL_VEEAMSQL2012:Buffer_Manager None readahead_pages/sec', parameters={}, labels=[])
    Service(item='MSSQL_VEEAMSQL2012:Buffer_Manager None page_reads/sec', parameters={}, labels=[])
    Service(item='MSSQL_VEEAMSQL2012:Buffer_Manager None page_writes/sec', parameters={}, labels=[])
    """
    yield from discovery_mssql_counters_generic(
        section,
        {"page_reads/sec", "page_writes/sec", "page_lookups/sec"},
        dflt={},
    )


def _check_common(
    value_store: ValueStore,
    time_point: float,
    node_name: str,
    item: str,
    params: Parameters,
    section: Section,
) -> CheckResult:
    counters, _counter = get_item(item, section)
    now = counters.get("utc_time", time_point)

    for counter_key, title in (p for p in (
        ("page_reads/sec", "Reads"),
        ("page_writes/sec", "Writes"),
        ("page_lookups/sec", "Lookups"),
    ) if p[0] in counters):
        try:
            yield from check_levels(
                value=get_rate(
                    value_store,
                    "mssql_counters.pageactivity.%s.%s.%s" % (node_name or None, item, counter_key),
                    now,
                    counters[counter_key],
                ),
                levels_upper=params.get(counter_key),
                render_func=lambda v, n=node_name, t=title: ("%s%s: %.1f/s" %
                                                             (n and "[%s] " % n, t, v)),
                metric_name=counter_key.replace("/sec", "_per_second"),
            )
        except GetRateError:
            yield IgnoreResults("Cannot calculate rates yet")


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
    ...   for result in _check_base(vs, 1597839904 + i, "MSSQL_VEEAMSQL2012:Buffer_Manager None", {}, {
    ...       ('MSSQL_VEEAMSQL2012:Buffer_Manager', 'None'): {'page_lookups/sec': 6649047653 + i, 'readahead_pages/sec': 1424319, 'page_reads/sec': 3220650 + i, 'page_writes/sec': 3066377 + i},
    ...   }):
    ...     print(result)
    Cannot calculate rates yet
    Cannot calculate rates yet
    Cannot calculate rates yet
    Result(state=<State.OK: 0>, summary='Reads: 1.0/s', details='Reads: 1.0/s')
    Metric('page_reads_per_second', 1.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='Writes: 1.0/s', details='Writes: 1.0/s')
    Metric('page_writes_per_second', 1.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='Lookups: 1.0/s', details='Lookups: 1.0/s')
    Metric('page_lookups_per_second', 1.0, levels=(None, None), boundaries=(None, None))
    """
    yield from _check_common(value_store, time_point, "", item, params, section)


def check_mssql_counters_pageactivity(
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
    ...   for result in _cluster_check_base(vs, 1597839904 + i, "MSSQL_VEEAMSQL2012:Buffer_Manager None", {}, {"node1": {
    ...       ('MSSQL_VEEAMSQL2012:Buffer_Manager', 'None'): {'page_lookups/sec': 6649047653 + i, 'readahead_pages/sec': 1424319, 'page_reads/sec': 3220650 + i, 'page_writes/sec': 3066377 + i},
    ...   }}):
    ...     print(result)
    Cannot calculate rates yet
    Cannot calculate rates yet
    Cannot calculate rates yet
    Result(state=<State.OK: 0>, summary='[node1] Reads: 1.0/s', details='[node1] Reads: 1.0/s')
    Metric('page_reads_per_second', 1.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='[node1] Writes: 1.0/s', details='[node1] Writes: 1.0/s')
    Metric('page_writes_per_second', 1.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='[node1] Lookups: 1.0/s', details='[node1] Lookups: 1.0/s')
    Metric('page_lookups_per_second', 1.0, levels=(None, None), boundaries=(None, None))
    """
    for node_name, node_section in section.items():
        yield from _check_common(value_store, time_point, node_name, item, params, node_section)


def cluster_check_mssql_counters_pageactivity(
    item: str,
    params: Parameters,
    section: Mapping[str, Section],
) -> CheckResult:
    yield from _cluster_check_base(get_value_store(), time.time(), item, params, section)


register.check_plugin(
    name="mssql_counters_pageactivity",
    sections=['mssql_counters'],
    service_name="MSSQL %s Page Activity",
    discovery_function=discovery_mssql_counters_pageactivity,
    check_default_parameters={},
    check_ruleset_name="mssql_page_activity",
    check_function=check_mssql_counters_pageactivity,
    cluster_check_function=cluster_check_mssql_counters_pageactivity,
)
