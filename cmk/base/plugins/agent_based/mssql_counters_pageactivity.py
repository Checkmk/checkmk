#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
def check_mssql_counters_pageactivity(item, params, parsed):
    node_data = extract_item_data(item, parsed)

    if node_data is None:
        # Assume general connection problem to the database, which is reported
        # by the "X Instance" service and skip this check.
        raise MKCounterWrapped("Failed to connect to database")

    for node_name, counters in node_data.items():
        now = counters.get('utc_time')
        if now is None:
            now = time.time()

        node_info = ""
        if node_name:
            node_info = "[%s] " % node_name

        for counter_key, title in [
            ("page_reads/sec", "Reads"),
            ("page_writes/sec", "Writes"),
            ("page_lookups/sec", "Lookups"),
        ]:
            value = counters.get(counter_key)
            if value is None:
                continue

            rate = get_rate("mssql_counters.pageactivity.%s.%s.%s" % (node_name, item, counter_key),
                            now, value)
            infotext = "%s%s: %.1f/s" % (node_info, title, rate)
            node_info = ""

            state = 0
            warn, crit = params.get(counter_key, (None, None))
            if crit is not None and rate >= crit:
                state = 2
            elif warn is not None and rate >= warn:
                state = 1
            if state:
                infotext += " (warn/crit at %.1f/%.1f per second)" % (warn, crit)

            yield state, infotext, [(counter_key, rate, warn, crit)]


check_info['mssql_counters.pageactivity'] = {
    'inventory_function': lambda parsed: inventory_mssql_counters_generic(
        parsed, ["page_reads/sec", "page_writes/sec", "page_lookups/sec"], dflt={}),
    'check_function': check_mssql_counters_pageactivity,
    'service_description': "MSSQL %s Page Activity",
    'has_perfdata': True,
    'group': "mssql_page_activity",
    'node_info': True,
}
"""
