#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
def check_mssql_counters_transactions(item, params, parsed):
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
            ('transactions/sec', 'Transactions'),
            ('write_transactions/sec', 'Write Transactions'),
            ('tracked_transactions/sec', 'Tracked Transactions'),
        ]:
            value = counters.get(counter_key)
            if value is None:
                continue

            rate = get_rate("mssql_counters.transactions.%s.%s.%s" % (node_name, item, counter_key),
                            now, value)
            infotext = "%s%s: %.1f/s" % (node_info, title, rate)
            node_info = ""
            yield 0, infotext, [(counter_key, rate)]


check_info['mssql_counters.transactions'] = {
    'inventory_function': lambda parsed: inventory_mssql_counters_generic(
        parsed, ['transactions/sec', 'write_transactions/sec', 'tracked_transactions/sec']),
    'check_function': check_mssql_counters_transactions,
    'service_description': "MSSQL %s Transactions",
    'has_perfdata': True,
    'node_info': True,
}
"""
