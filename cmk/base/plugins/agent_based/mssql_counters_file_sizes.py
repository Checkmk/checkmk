#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

from .agent_based_api.v1 import (
    Metric,
    register,
    render,
    check_levels,
)
from .agent_based_api.v1.type_defs import (
    Parameters,
    CheckResult,
    DiscoveryResult,
)

from .utils.mssql_counters import Section, discovery_mssql_counters_generic, get_int, get_item


def discovery_mssql_counters_file_sizes(section: Section) -> DiscoveryResult:
    """
    >>> for result in discovery_mssql_counters_file_sizes({
    ...   ('MSSQL_VEEAMSQL2012', 'tempdb'): {'data_file(s)_size_(kb)': 164928, 'log_file(s)_size_(kb)': 13624, 'log_file(s)_used_size_(kb)': 8768, 'percent_log_used': 64, 'active_transactions': 0}
    ... }):
    ...   print(result)
    Service(item='MSSQL_VEEAMSQL2012 tempdb data_file(s)_size_(kb)', parameters={}, labels=[])
    Service(item='MSSQL_VEEAMSQL2012 tempdb log_file(s)_size_(kb)', parameters={}, labels=[])
    Service(item='MSSQL_VEEAMSQL2012 tempdb log_file(s)_used_size_(kb)', parameters={}, labels=[])
    Service(item='MSSQL_VEEAMSQL2012 tempdb percent_log_used', parameters={}, labels=[])
    Service(item='MSSQL_VEEAMSQL2012 tempdb active_transactions', parameters={}, labels=[])
    """
    yield from discovery_mssql_counters_generic(
        section, {'data_file(s)_size_(kb)', 'log_file(s)_size_(kb)', 'log_file(s)_used_size_(kb)'},
        dflt={})


def _check_mssql_file_sizes(
    node_info: str,
    item: str,
    params: Parameters,
    section: Section,
) -> CheckResult:
    counters, _counter = get_item(item, section)
    log_files_size = get_int(counters, "log_file(s)_size_(kb)")
    data_files_size = get_int(counters, "data_file(s)_size_(kb)")

    for size_kb, key, title in (
        (data_files_size, "data_files", "Data files"),
        (log_files_size, "log_files", "Log files total"),
    ):
        yield from check_levels(
            size_kb * 1024,
            levels_upper=params.get(key),
            render_func=lambda v, t=title: "%s%s: %s" % (node_info, t, render.bytes(v)),
            metric_name=key,
        )

    log_files_used = counters.get("log_file(s)_used_size_(kb)")
    if log_files_used is None:
        return

    levels_upper = params.get("log_files_used", (None, None))
    if isinstance(levels_upper[0], float) and log_files_size:
        yield from check_levels(
            100 * log_files_used / log_files_size,
            levels_upper=levels_upper,
            render_func=render.percent,
            label="Log files used",
        )
    else:
        yield from check_levels(
            log_files_used,
            levels_upper=levels_upper,
            render_func=render.bytes,
            label="Log files used",
        )
    yield Metric(
        "log_files_used",
        log_files_used,
        levels=levels_upper,
    )


def check_mssql_counters_file_sizes(
    item: str,
    params: Parameters,
    section: Section,
) -> CheckResult:
    """
    >>> for result in check_mssql_counters_file_sizes(
    ...   "MSSQL_VEEAMSQL2012 tempdb cache_hit_ratio", {}, {
    ...     ('MSSQL_VEEAMSQL2012', 'tempdb'): {'data_file(s)_size_(kb)': 164928, 'log_file(s)_size_(kb)': 13624, 'log_file(s)_used_size_(kb)': 8768, 'percent_log_used': 64, 'active_transactions': 0}
    ... }):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='Data files: 161 MiB', details='Data files: 161 MiB')
    Metric('data_files', 168886272.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='Log files total: 13.3 MiB', details='Log files total: 13.3 MiB')
    Metric('log_files', 13950976.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='Log files used: 8.56 KiB', details='Log files used: 8.56 KiB')
    Metric('log_files_used', 8768.0, levels=(None, None), boundaries=(None, None))
    """
    yield from _check_mssql_file_sizes("", item, params, section)


def cluster_check_mssql_counters_file_sizes(
    item: str,
    params: Parameters,
    section: Mapping[str, Section],
) -> CheckResult:
    """
    >>> for result in cluster_check_mssql_counters_file_sizes(
    ...     "MSSQL_VEEAMSQL2012 tempdb cache_hit_ratio", {}, {"node1": {
    ...       ('MSSQL_VEEAMSQL2012', 'tempdb'): {'data_file(s)_size_(kb)': 164928, 'log_file(s)_size_(kb)': 13624, 'log_file(s)_used_size_(kb)': 8768, 'percent_log_used': 64, 'active_transactions': 0}
    ... }}):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='[node1] Data files: 161 MiB', details='[node1] Data files: 161 MiB')
    Metric('data_files', 168886272.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='[node1] Log files total: 13.3 MiB', details='[node1] Log files total: 13.3 MiB')
    Metric('log_files', 13950976.0, levels=(None, None), boundaries=(None, None))
    Result(state=<State.OK: 0>, summary='Log files used: 8.56 KiB', details='Log files used: 8.56 KiB')
    Metric('log_files_used', 8768.0, levels=(None, None), boundaries=(None, None))
    """
    for node_name, node_section in section.items():
        yield from _check_mssql_file_sizes("[%s] " % node_name, item, params, node_section)


register.check_plugin(
    name="mssql_counters_file_sizes",
    sections=['mssql_counters'],
    service_name="MSSQL %s File Sizes",
    discovery_function=discovery_mssql_counters_file_sizes,
    check_default_parameters={},
    check_ruleset_name="mssql_file_sizes",
    check_function=check_mssql_counters_file_sizes,
    cluster_check_function=cluster_check_mssql_counters_file_sizes,
)
