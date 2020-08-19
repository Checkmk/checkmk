#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
def inventory_mssql_counters_cache_hits(parsed, want_counters):
    add_zero_based_services = host_extra_conf_merged(host_name(), inventory_mssql_counters_rules)\
                              .get('add_zero_based_services', False)

    for node_data in parsed.values():
        for (obj, instance), counters in parsed.items():
            for counter in counters:
                if counter not in want_counters:
                    continue

                if counters.get('%s_base' % counter, 0.0) == 0.0 \
                   and not add_zero_based_services:
                    continue

                yield "%s %s %s" % (obj, instance, counter), None


def check_mssql_counters_cache_hits(item, params, parsed):
    node_data = extract_item_data(item, parsed)

    if node_data is None:
        # Assume general connection problem to the database, which is reported
        # by the "X Instance" service and skip this check.
        raise MKCounterWrapped("Failed to connect to database")

    _obj, _instance, counter = item.split()
    for node_name, counters in node_data.items():
        value = counters.get(counter)
        base = counters.get("%s_base" % counter, 0)

        if value is None or base is None:
            # Assume general connection problem to the database, which is reported
            # by the "X Instance" service and skip this check.
            raise MKCounterWrapped("Failed to connect to database")

        if base == 0:
            base = 1
        perc = 100.0 * value / base

        node_info = ""
        if node_name:
            node_info = "[%s] " % node_name
        infotext = "%s%s" % (node_info, get_percent_human_readable(perc))
        state = 0
        if params:
            #TODO: Previously params=None(=dflt) in inventory_mssql_counters
            warn, crit = params
            if perc <= crit:
                state = 2
            elif perc <= warn:
                state = 1
            if state:
                infotext += " (warn/crit below %s/%s)" % (warn, crit)
        yield state, infotext, [(counter, perc)]


check_info['mssql_counters.cache_hits'] = {
    'inventory_function': lambda parsed: inventory_mssql_counters_cache_hits(
        parsed, ['cache_hit_ratio', 'log_cache_hit_ratio', 'buffer_cache_hit_ratio']),
    'check_function': check_mssql_counters_cache_hits,
    'service_description': "MSSQL %s",
    'has_perfdata': True,
    'node_info': True,
}
"""
