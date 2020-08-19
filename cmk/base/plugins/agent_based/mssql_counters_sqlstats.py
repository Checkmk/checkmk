#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
def inventory_mssql_counters_sqlstats(parsed, want_counters, dflt=None):
    for node_data in parsed.values():
        for (obj, instance), counters in parsed.items():
            for counter in counters:
                if counter not in want_counters:
                    continue
                yield "%s %s %s" % (obj, instance, counter), dflt


def check_mssql_counters_sqlstats(item, params, parsed):
    node_data = extract_item_data(item, parsed)

    if node_data is None:
        # Assume general connection problem to the database, which is reported
        # by the "X Instance" service and skip this check.
        raise MKCounterWrapped("Failed to connect to database")

    _obj, _instance, counter = item.split()
    for node_name, counters in node_data.items():
        value = counters.get(counter)
        if value is None:
            return

        now = counters.get('utc_time')
        if now is None:
            now = time.time()

        rate = get_rate("mssql_counters.sqlstats.%s.%s.%s" % (node_name, item, counter), now, value)
        node_info = ""
        if node_name:
            node_info = "[%s] " % node_name
        infotext = "%s%.1f/sec" % (node_info, rate)

        state = 0
        warn, crit = params.get(counter, (None, None))
        if crit is not None and rate >= crit:
            state = 2
        elif warn is not None and rate >= warn:
            state = 1
        if state:
            infotext += " (warn/crit at %.1f/%.1f per second)" % (warn, crit)

        yield state, infotext, [(counter, rate, warn, crit)]


check_info["mssql_counters.sqlstats"] = {
    "inventory_function": lambda parsed: inventory_mssql_counters_sqlstats(
        parsed, ["batch_requests/sec", "sql_compilations/sec", "sql_re-compilations/sec"], dflt={}),
    "check_function": check_mssql_counters_sqlstats,
    "service_description": "MSSQL %s",
    "has_perfdata": True,
    "group": "mssql_stats",
    'node_info': True,
}
"""
