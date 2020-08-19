#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
def check_mssql_file_sizes(item, params, parsed):
    node_data = extract_item_data(item, parsed)

    if node_data is None:
        # Assume general connection problem to the database, which is reported
        # by the "X Instance" service and skip this check.
        raise MKCounterWrapped("Failed to connect to database")

    if not params:
        params = {}

    for node_name, counters in node_data.items():
        node_info = ""
        if node_name:
            node_info = "[%s] " % node_name

        log_files_size = counters.get("log_file(s)_size_(kb)")
        for val_bytes, key, title in [
            (counters.get("data_file(s)_size_(kb)"), "data_files", "Data files"),
            (log_files_size, "log_files", "Log files total"),
        ]:
            if val_bytes is None:
                continue

            val_bytes = val_bytes * 1024
            infotext = "%s%s: %s" % (node_info, title, get_bytes_human_readable(val_bytes))
            node_info = ""

            state = 0
            warn, crit = params.get(key, (None, None))
            if crit is not None and val_bytes >= crit:
                state = 2
            elif warn is not None and val_bytes >= warn:
                state = 1
            if state:
                infotext += " (warn/crit at %s/%s)" % (get_bytes_human_readable(warn),
                                                       get_bytes_human_readable(crit))

            yield state, infotext, [(key, val_bytes, warn, crit)]

        log_files_used = counters.get("log_file(s)_used_size_(kb)")
        infotext = "Log files used: %s" % get_bytes_human_readable(log_files_used)
        try:
            log_files_used_perc = 100.0 * log_files_used / log_files_size
            infotext += ", %s" % get_percent_human_readable(log_files_used_perc)
        except (TypeError, ZeroDivisionError):
            log_files_used_perc = None

        warn, crit = params.get("log_files_used", (None, None))
        if isinstance(crit, float) and log_files_used_perc is not None:
            log_files_used_value = log_files_used_perc
            readable_f = get_percent_human_readable
        elif isinstance(warn, int):
            log_files_used_value = log_files_used
            readable_f = get_bytes_human_readable
        else:
            yield 0, infotext, [("log_files_used", log_files_used, warn, crit)]
            continue

        state = 0
        if crit is not None and log_files_used_value >= crit:
            state = 2
        elif warn is not None and log_files_used_value >= warn:
            state = 1
        if state:
            infotext += " (warn/crit at %s/%s)" % (readable_f(warn), readable_f(crit))
        yield state, infotext, [("log_files_used", log_files_used, warn, crit)]


check_info['mssql_counters.file_sizes'] = {
    'inventory_function': lambda parsed: inventory_mssql_counters_generic(
        parsed, ['data_file(s)_size_(kb)', 'log_file(s)_size_(kb)', 'log_file(s)_used_size_(kb)'],
        dflt={}),
    'check_function': check_mssql_file_sizes,
    'service_description': "MSSQL %s File Sizes",
    'has_perfdata': True,
    'group': "mssql_file_sizes",
    'node_info': True,
}
"""
